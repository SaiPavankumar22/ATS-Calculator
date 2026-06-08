"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
PROMPTS_DIR = PROJECT_ROOT / "prompts" / "templates"

DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
OPEN_BROWSER = os.getenv("OPEN_BROWSER", "true" if DEBUG else "false").lower() in (
    "true",
    "1",
    "yes",
)
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "true" if DEBUG else "false").lower() in (
    "true",
    "1",
    "yes",
)
CACHE_DIR = PROJECT_ROOT / "cache"
