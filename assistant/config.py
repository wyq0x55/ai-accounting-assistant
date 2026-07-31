"""Application configuration loaded from environment variables.

Keeps configuration separate from code. All mutable values come from the
environment (see .env.example); nothing is hard-coded.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("ASSISTANT_DATA_DIR", BASE_DIR / "data"))
LOG_DIR = Path(os.getenv("ASSISTANT_LOG_DIR", BASE_DIR / "logs"))


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    JSON_AS_ASCII = False

    # Database
    DATA_DIR = DATA_DIR
    LOG_DIR = LOG_DIR
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{DATA_DIR / 'assistant.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    # Classification thresholds
    AUTO_CONFIRM_THRESHOLD = float(os.getenv("AUTO_CONFIRM_THRESHOLD", "0.9"))
    REVIEW_THRESHOLD = float(os.getenv("REVIEW_THRESHOLD", "0.6"))

    # LLM (OpenAI-compatible; e.g. Ollama/llama.cpp/vLLM)
    LLM_BASE_URL = os.getenv("OPENAI_BASE_URL", "")  # e.g. http://ollama:11434/v1
    LLM_API_KEY = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL = os.getenv("OPENAI_MODEL", "")        # e.g. qwen2.5:7b
    LLM_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "30"))

    # Actual Budget bridge
    BRIDGE_BASE_URL = os.getenv("BRIDGE_BASE_URL", "")  # e.g. http://bridge:5008
    ACTUAL_DEFAULT_ACCOUNT_ID = os.getenv("ACTUAL_DEFAULT_ACCOUNT_ID", "")

    @classmethod
    def ensure_dirs(cls) -> None:
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
