"""
Utility functions for LLM providers.
"""

import logging
from typing import Any

from services.models import NebiusProvider
from services.prompt import NEBIUS_API_KEY

logger = logging.getLogger(__name__)


def extract_json_from_response(response_text: str) -> str:
    """Extract JSON content from markdown code blocks."""
    response_text = response_text.strip()
    if "<think>" in response_text:
        think_start = response_text.find("<think>")
        think_end = response_text.find("</think>")
        if think_start != -1 and think_end != -1:
            response_text = response_text[:think_start] + response_text[think_end + 8 :]

    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    return response_text


def initialize_llm_provider(model_name: str) -> Any:
    """Initialize the Nebius AI Studio LLM provider."""
    if not NEBIUS_API_KEY:
        raise ValueError(
            "NEBIUS_API_KEY is not set. Add your Nebius API key to the .env file."
        )

    logger.info("Using Nebius AI Studio provider with model %s", model_name)
    return NebiusProvider(api_key=NEBIUS_API_KEY)
