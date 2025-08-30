"""
Telephony utilities for common call management functions
"""

import logging
import asyncio
import os
from typing import Optional, Dict, Any
from datetime import datetime
from livekit import api
from livekit.agents import JobContext

logger = logging.getLogger("telephony-utils")


def parse_metadata(metadata) -> Dict[str, Any]:
    """
    Convert metadata to dict if it is a string, otherwise return as is.

    Args:
        metadata: Metadata as dict or JSON string

    Returns:
        Metadata as dict
    """
    if not metadata or metadata == "":
        return {}
    if isinstance(metadata, str):
        try:
            import json

            return json.loads(metadata)
        except Exception as e:
            logger.error(f"Failed to parse metadata string: {e}")
            return {}
    return metadata if isinstance(metadata, dict) else {}


async def transfer_call_to_human(ctx: JobContext, transfer_to_number: str, transfer_context: Dict[str, Any]) -> bool:
    """
    Transfer the current call to a human operator

    Args:
        ctx: Job context
        transfer_to_number: Phone number to transfer to
        transfer_context: Context information for the transfer

    Returns:
        True if transfer initiated successfully, False otherwise
    """
    try:
        logger.info(f"Initiating transfer to human operator: {transfer_to_number}")
        sip_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")

        # Create a new SIP participant for the human operator
        sip_participant = await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=sip_trunk_id,
                sip_call_to=transfer_to_number,
                participant_identity=transfer_to_number,
                participant_name="Human Operator",
                wait_until_answered=True,
            )
        )

        participant = await ctx.wait_for_participant(identity=transfer_to_number)
        logger.info(f"participant joined: {participant.identity}")

        await ctx.api.room.remove_participant(
            api.RoomParticipantIdentity(room=ctx.room.name, identity=ctx.room.local_participant.identity)
        )
        logger.info(f"Agent disconnected")

        logger.info(f"Successfully created SIP participant for human transfer: {sip_participant.participant_identity}")

        # Log transfer details
        transfer_log = {
            "transfer_to": transfer_to_number,
            "transfer_timestamp": datetime.now().isoformat(),
            "transfer_context": transfer_context,
            "sip_participant_id": sip_participant.participant_identity,
            "room_name": ctx.room.name,
        }

        logger.info(f"Call transfer initiated: {transfer_log}")

        return True

    except Exception as e:
        logger.error(f"Failed to transfer call to human: {e}")
        return False


async def end_call_gracefully(ctx: JobContext, reason: str = "Call ended") -> bool:
    """
    End the call gracefully with proper cleanup

    Args:
        ctx: Job context
        reason: Reason for ending the call

    Returns:
        True if call ended successfully, False otherwise
    """
    try:
        logger.info(f"Ending call gracefully: {reason}")

        # Delete the room to end the call
        await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))

        logger.info(f"Call ended successfully: {reason}")
        return True

    except Exception as e:
        logger.error(f"Error ending call: {e}")
        return False


def validate_phone_number(phone_number: str) -> bool:
    """
    Validate phone number format

    Args:
        phone_number: Phone number to validate

    Returns:
        True if valid, False otherwise
    """
    import re

    # Basic validation for international format
    pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone_number))


def format_call_duration(start_time: datetime) -> str:
    """
    Format call duration in a human-readable format

    Args:
        start_time: Call start time

    Returns:
        Formatted duration string
    """
    duration = (datetime.now() - start_time).total_seconds()

    if duration < 60:
        return f"{int(duration)} seconds"
    elif duration < 3600:
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes}m {seconds}s"
    else:
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        return f"{hours}h {minutes}m"


def prepare_transfer_context(
    call_metadata: Dict[str, Any], call_start_time: datetime, transfer_reason: str, conversation_summary: str = ""
) -> Dict[str, Any]:
    """
    Prepare context information for human transfer

    Args:
        call_metadata: Call metadata
        call_start_time: Call start time
        transfer_reason: Reason for transfer
        conversation_summary: Summary of conversation

    Returns:
        Transfer context dictionary
    """
    call_duration = (datetime.now() - call_start_time).total_seconds()

    return {
        "call_duration_seconds": call_duration,
        "call_duration_formatted": format_call_duration(call_start_time),
        "customer_info": {
            "name": call_metadata.get("customer_name"),
            "city": call_metadata.get("city"),
            "phone": call_metadata.get("phone_number"),
        },
        "call_type": call_metadata.get("call_type"),
        "transfer_reason": transfer_reason,
        "conversation_summary": conversation_summary,
        "transfer_timestamp": datetime.now().isoformat(),
        "call_start_time": call_start_time.isoformat(),
    }


def log_call_analytics(
    call_metadata: Dict[str, Any],
    call_start_time: datetime,
    transfer_attempts: int = 0,
    call_outcome: str = "completed",
) -> Dict[str, Any]:
    """
    Log call analytics for reporting

    Args:
        call_metadata: Call metadata
        call_start_time: Call start time
        transfer_attempts: Number of transfer attempts
        call_outcome: Outcome of the call

    Returns:
        Analytics data dictionary
    """
    call_duration = (datetime.now() - call_start_time).total_seconds()

    analytics = {
        "duration_seconds": call_duration,
        "duration_formatted": format_call_duration(call_start_time),
        "call_type": call_metadata.get("call_type"),
        "transfer_attempts": transfer_attempts,
        "call_outcome": call_outcome,
        "phone_number": call_metadata.get("phone_number"),
        "customer_name": call_metadata.get("customer_name"),
        "city": call_metadata.get("city"),
        "timestamp": datetime.now().isoformat(),
        "call_start_time": call_start_time.isoformat(),
    }

    logger.info(f"Call analytics: {analytics}")
    return analytics


async def wait_for_participant_with_timeout(ctx: JobContext, timeout: int = 30) -> Optional[Any]:
    """
    Wait for participant to connect with timeout

    Args:
        ctx: Job context
        timeout: Timeout in seconds

    Returns:
        Participant object if connected, None if timeout
    """
    try:
        logger.info(f"Waiting for participant connection (timeout: {timeout}s)...")
        participant = await asyncio.wait_for(ctx.wait_for_participant(), timeout=timeout)
        logger.info(f"Participant connected: {participant.identity}")
        return participant
    except asyncio.TimeoutError:
        logger.error(f"Participant connection timeout after {timeout} seconds")
        return None
    except Exception as e:
        logger.error(f"Error waiting for participant: {e}")
        return None


def get_call_metadata_from_context(ctx: JobContext) -> Dict[str, Any]:
    """
    Extract call metadata from job context

    Args:
        ctx: Job context

    Returns:
        Call metadata dictionary
    """
    metadata = ctx.job.metadata if ctx and ctx.job else {}
    metadata = parse_metadata(metadata)

    return {
        "phone_number": metadata.get("phone_number"),
        "customer_name": metadata.get("customer_name"),
        "city": metadata.get("city"),
        "transfer_to": metadata.get("transfer_to"),
        "call_type": "outbound" if metadata.get("phone_number") else "inbound",
    }
