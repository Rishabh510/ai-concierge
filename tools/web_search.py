"""
Web Search Tool using Serper and Google Gemini
"""

import os
import requests
import logging
from typing import Dict, Any, List
from constants import SERPER_API_KEY

logger = logging.getLogger("web-search-tool")


def web_search(query: str, num_results: int = 5) -> Dict[str, Any]:
    """
    Search the web using Serper.

    Args:
        query: The search query.
        num_results: Number of search results to return.

    Returns:
        A dictionary containing the search results.
    """
    if not SERPER_API_KEY:
        logger.error("SERPER_API_KEY is not configured.")
        return {"error": "Search API key is not configured."}

    try:
        search_payload = {'q': query, 'gl': 'in', 'hl': 'en', 'num': num_results}
        headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
        response = requests.post('https://google.serper.dev/search', headers=headers, json=search_payload)
        response.raise_for_status()
        search_data = response.json()

        if not search_data.get("organic"):
            return {"results": []}

        return {"results": search_data['organic'][:num_results]}

    except requests.exceptions.RequestException as e:
        logger.error(f"Serper API request failed: {e}")
        return {"error": f"Search API request failed: {e}"}
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return {"error": f"An unexpected error occurred: {e}"}


def format_results_for_speech(search_results: List[Dict[str, Any]]) -> str:
    """
    Formats the search results for text-to-speech output.

    Args:
        search_results: A list of search result items.

    Returns:
        A formatted string for speech.
    """
    if not search_results:
        return "I couldn't find any information for that query."

    # Combine all snippets into one text
    combined_snippets = "\n\n".join(
        [
            f"{i+1}. {result['title']}\n{result['snippet']}\nSource: {result['link']}"
            for i, result in enumerate(search_results)
        ]
    )

    return f"Here are the top results I found:\n\n{combined_snippets}"
