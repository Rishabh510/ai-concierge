import os
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

import boto3
from livekit import api
from livekit.agents import JobContext

logger = logging.getLogger(__name__)


@dataclass
class RecordingConfig:
    """Configuration for audio recording"""

    s3_bucket: str
    s3_region: str
    s3_access_key: str
    s3_secret_key: str
    recording_enabled: bool = True
    file_format: str = "ogg"  # ogg, mp4, webm
    audio_only: bool = True


class RecordingService:
    """Service for managing LiveKit audio recordings and S3 uploads"""

    def __init__(self, config: RecordingConfig):
        self.config = config
        self.egress_id: Optional[str] = None
        self.recording_started = False

        # Initialize S3 client if recording is enabled
        if config.recording_enabled:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=config.s3_access_key,
                aws_secret_access_key=config.s3_secret_key,
                region_name=config.s3_region,
            )

    async def start_recording(self, ctx: JobContext, room_name: str) -> bool:
        """Start recording the room audio and upload to S3"""
        if not self.config.recording_enabled:
            logger.info("Recording is disabled, skipping")
            return False

        try:
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recordings/{room_name}_{timestamp}.{self.config.file_format}"

            # Create recording request
            if self.config.file_format == "ogg":
                file_type = api.EncodedFileType.OGG
            elif self.config.file_format == "mp4":
                file_type = api.EncodedFileType.MP4
            elif self.config.file_format == "webm":
                file_type = api.EncodedFileType.WEBM
            else:
                file_type = api.EncodedFileType.OGG

            # Configure S3 upload
            s3_upload = api.S3Upload(
                bucket=self.config.s3_bucket,
                region=self.config.s3_region,
                access_key=self.config.s3_access_key,
                secret=self.config.s3_secret_key,
            )

            # Create egress request
            egress_request = api.RoomCompositeEgressRequest(
                room_name=room_name,
                audio_only=self.config.audio_only,
                file_outputs=[api.EncodedFileOutput(file_type=file_type, filepath=filename, s3=s3_upload)],
            )

            # Start the recording
            logger.info(f"Starting audio recording for room {room_name}")
            response = await ctx.api.egress.start_room_composite_egress(egress_request)

            self.egress_id = response.egress_id
            self.recording_started = True

            logger.info(f"Recording started successfully with egress ID: {self.egress_id}")
            logger.info(f"Recording will be saved to S3: s3://{self.config.s3_bucket}/{filename}")

            return True

        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False

    async def stop_recording(self, ctx: JobContext) -> bool:
        """Stop the current recording"""
        if not self.egress_id or not self.recording_started:
            logger.info("No active recording to stop")
            return True

        try:
            logger.info(f"Stopping recording with egress ID: {self.egress_id}")

            # Stop the egress
            await ctx.api.egress.stop_egress(api.StopEgressRequest(egress_id=self.egress_id))

            self.egress_id = None
            self.recording_started = False

            logger.info("Recording stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return False

    async def get_recording_status(self, ctx: JobContext) -> Optional[Dict[str, Any]]:
        """Get the status of the current recording"""
        if not self.egress_id:
            return None

        try:
            response = await ctx.api.egress.get_egress(api.GetEgressRequest(egress_id=self.egress_id))

            return {
                "egress_id": response.egress_id,
                "status": response.status,
                "started_at": response.started_at,
                "ended_at": response.ended_at,
                "error": response.error,
            }

        except Exception as e:
            logger.error(f"Failed to get recording status: {e}")
            return None


def create_recording_config_from_env() -> RecordingConfig:
    """Create recording configuration from environment variables"""
    return RecordingConfig(
        s3_bucket=os.getenv("S3_RECORDING_BUCKET", ""),
        s3_region=os.getenv("S3_RECORDING_REGION", "us-east-1"),
        s3_access_key=os.getenv("AWS_ACCESS_KEY_ID", ""),
        s3_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        recording_enabled=os.getenv("ENABLE_AUDIO_RECORDING", "false").lower() == "true",
        file_format=os.getenv("RECORDING_FILE_FORMAT", "ogg"),
        audio_only=os.getenv("RECORDING_AUDIO_ONLY", "true").lower() == "true",
    )


async def setup_recording_service(ctx: JobContext, room_name: str) -> Optional[RecordingService]:
    """Set up and start recording service for the room"""
    config = create_recording_config_from_env()

    if not config.recording_enabled:
        logger.info("Audio recording is disabled")
        return None

    # Validate required configuration
    if not all([config.s3_bucket, config.s3_access_key, config.s3_secret_key]):
        logger.warning("S3 recording configuration incomplete, recording disabled")
        return None

    recording_service = RecordingService(config)

    # Start recording
    success = await recording_service.start_recording(ctx, room_name)
    if not success:
        logger.error("Failed to start recording service")
        return None

    return recording_service
