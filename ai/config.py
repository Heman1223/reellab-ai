"""Configuration for the ReelLab AI service.

Reads the same root `.env` the backend uses, so the two services cannot drift
on things like which model is configured.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def find_repo_root(start: Path) -> Path:
    """Walk up until we find the directory holding both `shared/` and `data/`."""
    current = start.resolve()
    for _ in range(10):
        if (current / "shared" / "schemas").is_dir() and (current / "data").is_dir():
            return current
        if current.parent == current:
            break
        current = current.parent
    return Path.cwd()


REPO_ROOT = find_repo_root(Path(__file__).parent)
DATA_DIR = REPO_ROOT / "data"
MOCK_DIR = DATA_DIR / "mock_personas"
EVALUATION_DIR = DATA_DIR / "evaluation"

load_dotenv(REPO_ROOT / ".env")


def _int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("AI_HOST", "0.0.0.0")
    port: int = _int("AI_PORT", 8000)
    log_level: str = os.getenv("AI_LOG_LEVEL", "info")

    provider: str = os.getenv("AI_PROVIDER", "mock")
    api_key: str = os.getenv("AI_API_KEY", "")
    multimodal_model: str = os.getenv("MULTIMODAL_MODEL", "claude-sonnet-5")
    reasoning_model: str = os.getenv("REASONING_MODEL", "claude-opus-5")

    # Cost guard rails. See docs/architecture.md#cost-aware-architecture.
    max_personas: int = _int("AI_MAX_PERSONAS", 25)
    request_timeout_seconds: int = _int("AI_REQUEST_TIMEOUT_SECONDS", 120)

    @property
    def is_mock_mode(self) -> bool:
        """True when no model will be called and fixtures are served instead."""
        return self.provider == "mock" or self.api_key.strip() == ""


settings = Settings()
