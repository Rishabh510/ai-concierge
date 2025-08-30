from livekit.agents import function_tool, RunContext


@function_tool()
async def weather_lookup(context: RunContext, location: str) -> dict[str, str]:
    """Look up weather information for a given location.

    Args:
        location: The location to look up weather information for

    Returns:
        Dictionary containing weather information
    """
    # This is a mock implementation - in real usage you'd call a weather API
    return {"weather": "sunny", "temperature": "72°F", "location": location}
