import logging
import os
import asyncio
from typing import Optional

from dotenv import load_dotenv
from livekit.agents import (
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    AgentFalseInterruptionEvent,
    NOT_GIVEN,
    cli,
    RoomInputOptions,
)
from livekit.plugins import noise_cancellation, silero
from livekit import api

from agents.master_agent import MasterAgent
from telephony_utils import wait_for_participant_with_timeout, parse_metadata


load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("master-agent")
CONTEXT_VARS = {
    "greeting_time": "evening",
    "salutation": "Mr.",
    "customer_name": "Rishabh",
    "city": "Bangalore",
    "call_type": "outbound",
    "transfer_to": "+918860932771",
}


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


async def _handle_agent_session(ctx: JobContext, agent: MasterAgent):
    """Handle the agent session lifecycle, including startup and cleanup."""
    try:
        session = AgentSession(
            min_endpointing_delay=0.8,
            max_endpointing_delay=2.5,
            vad=ctx.proc.userdata["vad"],
            preemptive_generation=True,
        )

        @session.on("agent_false_interruption")
        def _on_agent_false_interruption(ev: AgentFalseInterruptionEvent):
            logger.info("false positive interruption, resuming")
            session.generate_reply(instructions=ev.extra_instructions or NOT_GIVEN)

        room_input_options = RoomInputOptions(noise_cancellation=noise_cancellation.BVC(), close_on_disconnect=True)
        await session.start(room=ctx.room, agent=agent, room_input_options=room_input_options)
        logger.info("Agent session completed successfully")
    except Exception as e:
        logger.error(f"Error in agent session: {e}")
        try:
            await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
            logger.info("Room cleaned up after error")
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup room: {cleanup_error}")


async def entrypoint(ctx: JobContext):
    logger.info(f"Starting agent session for room {ctx.room.name}")

    metadata = parse_metadata(ctx.job.metadata)
    logger.info(f"Job metadata: {metadata}")
    phone_number = metadata.get("phone_number")

    if phone_number:
        logger.info(f"Processing outbound call to {phone_number}")
        sip_participant = await create_sip_participant(ctx, phone_number)
        if not sip_participant:
            logger.error("Failed to create SIP participant, ending session")
            return

        if not await wait_for_call_connection(ctx):
            logger.error("Call failed to connect, ending session")
            return
        logger.info(f"Outbound call established to {phone_number}")
    else:
        logger.info("Processing inbound call")
        participant = await ctx.wait_for_participant()
        logger.info(f"Inbound call from participant: {participant.identity}") if participant else ""

    await _handle_agent_session(ctx, MasterAgent())


async def entrypoint_webtest(ctx: JobContext):
    """Test agent with livekit playground"""
    logger.info(f"Starting agent session for room {ctx.room.name} and metadata {ctx.job.metadata}")
    ctx.log_context_fields = {"room": ctx.room.name}
    await _handle_agent_session(ctx, MasterAgent(context_vars=CONTEXT_VARS))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'
    )
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint_webtest, prewarm_fnc=prewarm))


"""NOTE:
Populate JOB_METADATA env variable (stringified json)
Example: '{"phone_number": "+919999999999", "customer_name": "Rishabh", "city": "Bangalore"}'
"""
