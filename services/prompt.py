"""
Prompts for Resume Evaluation System

This module contains all the prompts used by the resume evaluation system.
Centralizing prompts here makes them easier to maintain and update.
"""

import os
from dotenv import load_dotenv
from services.models import ModelProvider

# Load environment variables
load_dotenv()

# Constants
DEFAULT_MODEL_NAME = "gemma3:4b"
DEFAULT_PROVIDER = ModelProvider.OLLAMA

# Get model and provider from environment or use defaults
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", DEFAULT_MODEL_NAME)
PROVIDER = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER.value)

# Validate provider
if PROVIDER not in [p.value for p in ModelProvider]:
    PROVIDER = DEFAULT_PROVIDER.value

# Model-specific parameters
MODEL_PARAMETERS = {
    # Ollama models
    "qwen3:1.7b": {"temperature": 0.0, "top_p": 0.9},
    "gemma3:1b": {"temperature": 0.0, "top_p": 0.9},
    "qwen3:4b": {"temperature": 0.1, "top_p": 0.4},
    "gemma3:4b": {"temperature": 0.1, "top_p": 0.9},
    "gemma3:12b": {"temperature": 0.1, "top_p": 0.9},
    "mistral:7b": {"temperature": 0.1, "top_p": 0.9},
    # Nebius AI Studio models
    "google/gemma-3-27b-it": {"temperature": 0.1, "top_p": 0.9},
    "google/gemma-3-12b-it": {"temperature": 0.1, "top_p": 0.9},
    "meta-llama/Meta-Llama-3.1-70B-Instruct": {"temperature": 0.1, "top_p": 0.9},
    "meta-llama/Meta-Llama-3.1-8B-Instruct": {"temperature": 0.1, "top_p": 0.9},
    "mistralai/Mistral-Nemo-Instruct-2407": {"temperature": 0.1, "top_p": 0.9},
}

# Model provider mapping
# Maps model names to their provider
MODEL_PROVIDER_MAPPING = {
    # Ollama models
    "qwen3:1.7b": ModelProvider.OLLAMA,
    "gemma3:1b": ModelProvider.OLLAMA,
    "qwen3:4b": ModelProvider.OLLAMA,
    "gemma3:4b": ModelProvider.OLLAMA,
    "gemma3:12b": ModelProvider.OLLAMA,
    "mistral:7b": ModelProvider.OLLAMA,
    # Nebius AI Studio models
    "google/gemma-3-27b-it": ModelProvider.NEBIUS,
    "google/gemma-3-12b-it": ModelProvider.NEBIUS,
    "meta-llama/Meta-Llama-3.1-70B-Instruct": ModelProvider.NEBIUS,
    "meta-llama/Meta-Llama-3.1-8B-Instruct": ModelProvider.NEBIUS,
    "mistralai/Mistral-Nemo-Instruct-2407": ModelProvider.NEBIUS,
}

# Get API keys from environment
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "")
