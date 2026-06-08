"""
Model and provider configuration for the resume evaluation system.
Uses Nebius AI Studio exclusively.
"""

import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "google/gemma-3-27b-it")
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "")

MODEL_PARAMETERS = {
    "google/gemma-3-27b-it": {"temperature": 0.1, "top_p": 0.9},
    "google/gemma-3-12b-it": {"temperature": 0.1, "top_p": 0.9},
    "meta-llama/Meta-Llama-3.1-70B-Instruct": {"temperature": 0.1, "top_p": 0.9},
    "meta-llama/Meta-Llama-3.1-8B-Instruct": {"temperature": 0.1, "top_p": 0.9},
    "mistralai/Mistral-Nemo-Instruct-2407": {"temperature": 0.1, "top_p": 0.9},
}

SUPPORTED_MODELS = list(MODEL_PARAMETERS.keys())
