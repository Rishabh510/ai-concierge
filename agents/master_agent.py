import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from livekit.agents import Agent, function_tool, RunContext, get_job_context
from livekit.plugins import deepgram, openai, elevenlabs
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from .math_agent import MathAgent
from .weather_agent import WeatherAgent
from tools.budget_calculator import calculate_budget, format_budget_for_speech
from tools.web_search import web_search as perform_web_search, format_results_for_speech
from telephony_utils import (
    transfer_call_to_human,
    end_call_gracefully,
    prepare_transfer_context,
    log_call_analytics,
    get_call_metadata_from_context,
    validate_phone_number,
)
import re
from livekit import rtc
from livekit.agents.voice import ModelSettings
from typing import AsyncIterable
from constants import SYSTEM_PROMPT
from livekit.agents import mcp

logger = logging.getLogger("master-agent")


class MasterAgent(Agent):
    """Master agent that can hand off to specialized agents with enhanced call management"""

    def __init__(self, chat_ctx=None, context_vars=None):
        instructions = SYSTEM_PROMPT
        if context_vars:
            instructions = instructions.format(
                customer_name=context_vars.get("customer_name"), city=context_vars.get("city")
            )

        super().__init__(
            instructions=instructions,
            stt=deepgram.STT(),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=elevenlabs.TTS(voice_id="H8bdWZHK2OgZwTN7ponr"),
            turn_detection=MultilingualModel(),
            chat_ctx=chat_ctx,
            mcp_servers=[],
        )

        self.call_metadata = context_vars or {}
        self.call_start_time = datetime.now()
        self.transfer_attempts = 0
        self.max_transfer_attempts = 3

    # Overriding TTS node to add pronunciation rules
    async def tts_node(self, text: AsyncIterable[str], model_settings: ModelSettings) -> AsyncIterable[rtc.AudioFrame]:
        # Pronunciation replacements for common technical terms and abbreviations.
        # Support for custom pronunciations depends on the TTS provider.
        pronunciations = {"Meragi": "Meh raagi"}

        async def adjust_pronunciation(input_text: AsyncIterable[str]) -> AsyncIterable[str]:
            async for chunk in input_text:
                modified_chunk = chunk

                # Apply pronunciation rules
                for term, pronunciation in pronunciations.items():
                    # Use word boundaries to avoid partial replacements
                    modified_chunk = re.sub(rf'\b{term}\b', pronunciation, modified_chunk, flags=re.IGNORECASE)

                yield modified_chunk

        # Process with modified text through base TTS implementation
        async for frame in Agent.default.tts_node(self, adjust_pronunciation(text), model_settings):
            yield frame

    async def on_enter(self):
        """Enhanced entry point with call context awareness to populate dynamic variables"""
        ctx = get_job_context()
        if ctx:
            # Extract call metadata using utility function, but do not overwrite existing fields with None
            new_metadata = get_call_metadata_from_context(ctx)
            for k, v in new_metadata.items():
                if v is not None:
                    self.call_metadata[k] = v
            logger.info(f"Starting {self.call_metadata['call_type']} call with metadata: {self.call_metadata}")

        # First greeting message
        await self.session.generate_reply(
            user_input=f"Good {self.call_metadata.get('greeting_time', 'evening')}, {self.call_metadata.get('salutation', '')} {self.call_metadata.get('customer_name', '')}. How can I help you?",
            allow_interruptions=True,
        )

    async def on_exit(self):
        """Enhanced exit handling with call analytics"""
        # Use utility function for analytics
        log_call_analytics(self.call_metadata, self.call_start_time, self.transfer_attempts, "completed")
        ctx = get_job_context()
        if ctx is not None:
            await end_call_gracefully(ctx, "User requested call end")

    @function_tool()
    async def handoff_to_math_agent(self, context: RunContext):
        """Transfer the user to a specialized math agent for calculations.

        Use this when the user needs mathematical calculations, arithmetic operations,
        or any computational tasks.
        """
        await self.session.generate_reply(
            instructions="I'll transfer you to our math specialist who can help with calculations."
        )
        return "Transferring to math specialist", MathAgent(chat_ctx=self.chat_ctx)

    @function_tool()
    async def handoff_to_weather_agent(self, context: RunContext):
        """Transfer the user to a specialized weather agent for weather information.

        Use this when the user asks about weather, temperature, climate,
        or weather conditions for any location.
        """
        await self.session.generate_reply(
            instructions="I'll transfer you to our weather specialist who can provide weather information."
        )
        return "Transferring to weather specialist", WeatherAgent(chat_ctx=self.chat_ctx)

    @function_tool()
    async def end_call(self, context: RunContext):
        """End the current call when the user requests to hang up or end the conversation.

        Use this when the user says goodbye, wants to hang up, end the call,
        or indicates they are done with the conversation.
        """
        await self.session.generate_reply(instructions="Thank you for calling. Have a great day!")

        # Use utility function to end call gracefully
        ctx = get_job_context()
        if ctx is not None:
            await end_call_gracefully(ctx, "User requested call end")

        return "Call ended successfully"

    @function_tool()
    async def transfer_to_human(self, context: RunContext):
        """Transfer the call to a human operator when requested.

        Use this when the user explicitly asks to speak with a human,
        has complex issues that require human intervention, or when
        the conversation needs to be escalated.
        """
        self.transfer_attempts += 1

        if self.transfer_attempts > self.max_transfer_attempts:
            await self.session.generate_reply(
                instructions="I understand you'd like to speak with a human, but I'm unable to transfer you at the moment. Let me help you with your wedding planning needs instead."
            )
            return "Transfer limit exceeded, continuing with AI assistance"

        # Get transfer number from metadata
        transfer_to_number = self.call_metadata.get("transfer_to")
        if not transfer_to_number:
            await self.session.generate_reply(
                instructions="I apologize, but I'm unable to transfer you to a human operator at the moment. Let me help you with your wedding planning needs instead."
            )
            return "No transfer number configured, continuing with AI assistance"

        # Validate transfer number
        if not validate_phone_number(transfer_to_number):
            await self.session.generate_reply(
                instructions="I apologize, but there's an issue with the transfer system. Let me help you with your wedding planning needs instead."
            )
            return "Invalid transfer number, continuing with AI assistance"

        # Prepare transfer context
        transfer_reason = context.user_message if hasattr(context, 'user_message') else "User requested human transfer"

        transfer_context = prepare_transfer_context(
            self.call_metadata, self.call_start_time, transfer_reason, "Customer requested human assistance"
        )

        logger.info(f"Attempting transfer to human operator: {transfer_to_number}")

        await self.session.generate_reply(
            instructions="I understand you'd like to speak with a human representative. Let me transfer you to one of our wedding experts who can assist you better."
        )

        # Attempt to transfer the call
        ctx = get_job_context()
        if ctx:
            try:
                # Initiate transfer to human operator
                transfer_success = await transfer_call_to_human(ctx, transfer_to_number, transfer_context)

                if transfer_success:
                    logger.info(f"Call successfully transferred to human operator: {transfer_to_number}")
                    return "Call transferred to human operator successfully"
                else:
                    # If transfer fails, continue with AI assistance
                    await self.session.generate_reply(
                        instructions="I apologize, but I'm having trouble connecting you to a human operator right now. Let me continue helping you with your wedding planning needs."
                    )
                    return "Transfer failed, continuing with AI assistance"

            except Exception as e:
                logger.error(f"Error during human transfer: {e}")
                await self.session.generate_reply(
                    instructions="I apologize, but there was an issue with the transfer. Let me continue helping you with your wedding planning needs."
                )
                return "Transfer error, continuing with AI assistance"

        return "Transfer attempted"

    @function_tool()
    async def web_search(self, context: RunContext, query: str, num_results: int = 3):
        """Search the web for information.

        Use this when the user specifically asks to search the web for information.

        Args:
            query: The search query to find relevant web content.
            num_results: Number of search results to return (default: 3, max: 10).
        """
        try:
            logger.info(f"Performing web search for query: '{query}'")

            search_data = await asyncio.to_thread(
                perform_web_search,
                query=query,
                num_results=num_results
            )

            if "error" in search_data:
                raise Exception(search_data["error"])

            # The instruction will be to summarize these results
            formatted_results = format_results_for_speech(search_data.get("results", []))
            instruction = f"Summarize the following search results for the user's query '{query}':\n\n{formatted_results}"

            await self.session.generate_reply(
                instructions=instruction
            )

            return {
                "results_count": len(search_data.get("results", [])),
            }
        except Exception as e:
            logger.error(f"Error during web search: {e}")
            await self.session.generate_reply(
                instructions="I apologize, but I'm having trouble with the web search right now. Please try again later."
            )
            return {"error": "Web search failed"}

    @function_tool()
    async def budget_calculator(self, context: RunContext, number_of_events: int, number_of_people: int, location: str):
        """Calculate wedding service budget based on events, people count, and location.

        Use this when customers ask about costs, pricing, or budget estimates.
        This tool provides detailed budget breakdown for décor, photography, and catering services.

        Args:
            number_of_events: Number of wedding events (wedding, reception, etc.)
            number_of_people: Total number of guests across all events
            location: City/location for the wedding
        """
        try:
            logger.info(f"Calculating budget for {number_of_events} events, {number_of_people} people in {location}")

            budget_data = calculate_budget(number_of_events, number_of_people, location)
            formatted_budget = format_budget_for_speech(budget_data)

            await self.session.generate_reply(
                instructions=f"Share the budget calculation with the customer: {formatted_budget}"
            )

            # Log budget calculation for analytics
            budget_analytics = {
                "events": number_of_events,
                "people": number_of_people,
                "location": location,
                "total_budget": budget_data["total_budget_lakhs"],
                "customer_name": self.call_metadata.get("customer_name"),
                "phone_number": self.call_metadata.get("phone_number"),
            }
            logger.info(f"Budget calculated: {budget_analytics}")

            return {
                "budget_breakdown": budget_data,
                "formatted_response": formatted_budget,
                "total_budget_lakhs": budget_data["total_budget_lakhs"],
            }
        except Exception as e:
            logger.error(f"Error calculating budget: {e}")
            await self.session.generate_reply(
                instructions="I apologize, but I'm having trouble calculating the budget right now. Let me connect you with our wedding expert who can provide accurate pricing information."
            )
            return {"error": "Budget calculation failed"}
