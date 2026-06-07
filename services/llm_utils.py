"""
Utility functions for LLM providers.
"""

import logging
from typing import Any, Dict, Optional
from services.models import ModelProvider, OllamaProvider, NebiusProvider
from services.prompt import MODEL_PROVIDER_MAPPING, NEBIUS_API_KEY, PROVIDER

logger = logging.getLogger(__name__)


def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON content from markdown code blocks.

    Args:
        response_text: Text that may contain JSON wrapped in markdown code blocks

    Returns:
        Text with markdown code block syntax removed
    """

    response_text = response_text.strip()
    if "<think>" in response_text:
        think_start = response_text.find("<think>")
        think_end = response_text.find("</think>")
        if think_start != -1 and think_end != -1:
            response_text = response_text[:think_start] + response_text[think_end + 8 :]

    # Remove leading ```json if present
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    # Remove trailing ``` if present
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    return response_text


def initialize_llm_provider(model_name: str) -> Any:
    """
    Initialize the appropriate LLM provider based on the model name.

    Args:
        model_name: The name of the model to use

    Returns:
        An initialized LLM provider (either OllamaProvider or NebiusProvider)
    """
    model_provider = MODEL_PROVIDER_MAPPING.get(model_name, ModelProvider.OLLAMA)
    use_nebius = (
        PROVIDER == ModelProvider.NEBIUS.value
        or model_provider == ModelProvider.NEBIUS
    )

    if use_nebius:
        if not NEBIUS_API_KEY:
            logger.warning("⚠️ Nebius API key not found. Falling back to Ollama.")
            logger.info(f"🔄 Using Ollama provider with model {model_name}")
            return OllamaProvider()
        logger.info(f"🔄 Using Nebius AI Studio provider with model {model_name}")
        return NebiusProvider(api_key=NEBIUS_API_KEY)

    logger.info(f"🔄 Using Ollama provider with model {model_name}")
    return OllamaProvider()
