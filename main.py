import logging
import os
import asyncio
from typing import Optional

from dotenv import load_dotenv
from livekit.agents import (
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    MetricsCollectedEvent,
    AgentFalseInterruptionEvent,
    NOT_GIVEN,
    cli,
    metrics,
    RoomInputOptions,
)
from livekit.plugins import cartesia, openai, deepgram, noise_cancellation, silero, elevenlabs, google
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit import api

from agents.master_agent import MasterAgent
from telephony_utils import wait_for_participant_with_timeout, parse_metadata
from recording_service import setup_recording_service


load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("master-agent")


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def create_sip_participant(ctx: JobContext, phone_number: str) -> Optional[api.SIPParticipantInfo]:
    """Create SIP participant for outbound call with error handling"""
    try:
        sip_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
        if not sip_trunk_id:
            logger.error("SIP_OUTBOUND_TRUNK_ID not configured")
            return None

        logger.info(f"Creating SIP participant for {phone_number} using trunk {sip_trunk_id}")

        sip_participant = await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=sip_trunk_id,
                sip_call_to=phone_number,
                participant_identity=phone_number,
                wait_until_answered=True,
            )
        )

        logger.info(f"Successfully created SIP participant: {sip_participant}")
        return sip_participant

    except Exception as e:
        logger.error(f"Failed to create SIP participant: {e}")
        return None


async def wait_for_call_connection(ctx: JobContext, timeout: int = 30) -> bool:
    """Wait for call to connect with timeout"""
    participant = await wait_for_participant_with_timeout(ctx, timeout)
    return participant is not None


async def entrypoint(ctx: JobContext):
    logger.info(f"Starting agent session for room {ctx.room.name}")

    # Initialize recording service
    recording_service = None

    try:
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        logger.info("Successfully connected to room")

        # Set up audio recording service
        recording_service = await setup_recording_service(ctx, ctx.room.name)
        if recording_service:
            logger.info("Audio recording service initialized successfully")
        else:
            logger.info("Audio recording service not available or disabled")

        # Load variables from job metadata
        metadata = parse_metadata(ctx.job.metadata)

        logger.info(f"Job metadata: {metadata}")
        phone_number = metadata.get("phone_number")

        if phone_number:
            logger.info(f"Processing outbound call to {phone_number}")

            # Create SIP participant for outbound call
            sip_participant = await create_sip_participant(ctx, phone_number)
            if not sip_participant:
                logger.error("Failed to create SIP participant, ending session")
                return

            # Wait for the call to connect
            if not await wait_for_call_connection(ctx):
                logger.error("Call failed to connect, ending session")
                return

            logger.info(f"Outbound call established to {phone_number}")
        else:
            # Wait for the first participant to connect (inbound call)
            logger.info("Processing inbound call")
            participant = await ctx.wait_for_participant()
            logger.info(f"Inbound call from participant: {participant.identity}")

        # Set up metrics collection
        usage_collector = metrics.UsageCollector()

        def on_metrics_collected(agent_metrics: metrics.AgentMetrics):
            metrics.log_metrics(agent_metrics)
            usage_collector.collect(agent_metrics)

        # Create agent session with optimized settings
        session = AgentSession(
            vad=ctx.proc.userdata["vad"],
            # Optimized endpointing delays for better conversation flow
            min_endpointing_delay=0.8,  # Reduced for more responsive interactions
            max_endpointing_delay=2.5,  # Reduced for faster turn-taking
        )

        # Set up metrics collection
        session.on("metrics_collected", on_metrics_collected)

        # Start the agent session
        await session.start(
            room=ctx.room,
            agent=MasterAgent(),
            room_input_options=RoomInputOptions(
                # Enable background voice & noise cancellation for better call quality BVCTelephony()
                noise_cancellation=noise_cancellation.BVC()
            ),
        )

        logger.info("Agent session completed successfully")

    except Exception as e:
        logger.error(f"Error in agent session: {e}")
        # Attempt to clean up the room if there's an error
        try:
            await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
            logger.info("Room cleaned up after error")
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup room: {cleanup_error}")

    finally:
        # Stop recording if it was started
        if recording_service:
            try:
                await recording_service.stop_recording(ctx)
                logger.info("Recording stopped successfully")
            except Exception as e:
                logger.error(f"Failed to stop recording: {e}")


async def entrypoint_webtest(ctx: JobContext):
    """Test agent with livekit playground"""
    logger.info(f"Starting agent session for room {ctx.room.name} and metadata {ctx.job.metadata}")
    ctx.log_context_fields = {"room": ctx.room.name}

    # Initialize recording service
    recording_service = None

    try:
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        logger.info("Successfully connected to room")

        session = AgentSession(
            min_endpointing_delay=0.8,
            max_endpointing_delay=2.5,
            vad=ctx.proc.userdata["vad"],
            # allow the LLM to generate a response while waiting for the end of turn
            # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
            preemptive_generation=True,
        )

        context_vars = {
            "greeting_time": "morning",
            "salutation": "Mr.",
            "customer_name": "Rishabh",
            "city": "Bangalore",
            "call_type": "outbound",
            "transfer_to": "+918860932771",
        }

        # Set up audio recording service
        recording_service = await setup_recording_service(ctx, ctx.room.name)
        if recording_service:
            logger.info("Audio recording service initialized successfully")
        else:
            logger.info("Audio recording service not available or disabled")

        # 1.1. Handle false positive interruptions
        @session.on("agent_false_interruption")
        def _on_agent_false_interruption(ev: AgentFalseInterruptionEvent):
            logger.info("false positive interruption, resuming")
            session.generate_reply(instructions=ev.extra_instructions or NOT_GIVEN)

        # 2. Metrics collection, to measure pipeline performance
        # For more information, see https://docs.livekit.io/agents/build/metrics/
        usage_collector = metrics.UsageCollector()

        @session.on("metrics_collected")
        def _on_metrics_collected(ev: MetricsCollectedEvent):
            metrics.log_metrics(ev.metrics)
            usage_collector.collect(ev.metrics)

        async def log_usage():
            summary = usage_collector.get_summary()
            logger.info(f"Usage: {summary}")

        ctx.add_shutdown_callback(log_usage)  # Called after room is deleted/session terminates

        await session.start(
            room=ctx.room,
            agent=MasterAgent(context_vars=context_vars),
            room_input_options=RoomInputOptions(
                # For telephony applications, use `BVCTelephony` instead for best results
                noise_cancellation=noise_cancellation.BVC(),
                close_on_disconnect=True,
            ),
        )
    except Exception as e:
        logger.error(f"Error in agent session: {e}")
        # Attempt to clean up the room if there's an error
        try:
            await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
            logger.info("Room cleaned up after error")
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup room: {cleanup_error}")
    finally:
        # Stop recording if it was started
        if recording_service:
            try:
                await recording_service.stop_recording(ctx)
                logger.info("Recording stopped successfully")
            except Exception as e:
                logger.error(f"Failed to stop recording: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'
    )
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint_webtest, prewarm_fnc=prewarm))


"""NOTE:
Populate JOB_METADATA env variable (stringified json)
Example: '{"phone_number": "+919999999999", "customer_name": "Rishabh", "city": "Bangalore"}'
"""
