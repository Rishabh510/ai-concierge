from livekit.agents import Agent, function_tool, RunContext
from livekit.plugins import deepgram, openai, elevenlabs
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from tools.weather import weather_lookup


class WeatherAgent(Agent):
    """Specialized agent for weather information"""

    def __init__(self, chat_ctx=None):
        __name__ = "weather-agent"
        super().__init__(
            instructions="""You are a weather specialist assistant. Help users with weather information,
            temperature, climate, and weather conditions for any location. Be informative and helpful.
            Always use the weather_lookup tool to get current weather information.""",
            stt=deepgram.STT(),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=elevenlabs.TTS(voice_id="56AoDkrOh6qfVPDXZ7Pt"),
            turn_detection=MultilingualModel(),
            tools=[weather_lookup],
            chat_ctx=chat_ctx,
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="Introduce yourself as a weather specialist and ask what location's weather you can help with.",
            allow_interruptions=True,
        )

    @function_tool()
    async def return_to_main_agent(self, context: RunContext):
        """Return control back to the main assistant.

        Use this when the user wants to go back to general assistance or
        needs help with something other than weather.
        """
        from .master_agent import MasterAgent

        await self.session.generate_reply(
            instructions="I'll transfer you back to our main assistant who can help with other topics."
        )
        return "Returning to main assistant", MasterAgent(chat_ctx=self.chat_ctx)
