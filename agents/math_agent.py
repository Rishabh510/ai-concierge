from livekit.agents import Agent, function_tool, RunContext
from livekit.plugins import deepgram, openai, elevenlabs
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from tools.calculator import calculator


class MathAgent(Agent):
    """Specialized agent for mathematical calculations"""

    def __init__(self, chat_ctx=None):
        __name__ = "math-agent"
        super().__init__(
            instructions="""You are a math specialist assistant. Help users with calculations,
            arithmetic operations, and mathematical problems. Be precise and clear in your explanations.
            Always use the calculator tool for any mathematical operations.""",
            stt=deepgram.STT(),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=elevenlabs.TTS(voice_id="GHKbgpqchXOxta6X2lSd"),
            turn_detection=MultilingualModel(),
            tools=[calculator],
            chat_ctx=chat_ctx,
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="Introduce yourself as a math specialist and ask what calculation you can help with.",
            allow_interruptions=True,
        )

    @function_tool()
    async def return_to_main_agent(self, context: RunContext):
        """Return control back to the main assistant.

        Use this when the user wants to go back to general assistance or
        needs help with something other than math.
        """
        from .master_agent import MasterAgent

        await self.session.generate_reply(
            instructions="I'll transfer you back to our main assistant who can help with other topics."
        )
        return "Returning to main assistant", MasterAgent(chat_ctx=self.chat_ctx)
