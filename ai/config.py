"""Configuration for the ReelLab AI service.

Reads the same root `.env` the backend uses, so the two services cannot drift
on things like which model is configured.

Supported env var aliases (both names work, the first takes priority):
  GEMINI_API_KEY  / AI_API_KEY         — the API key for all providers
  VIDEO_PROVIDER  / MULTIMODAL_PROVIDER — provider for video analysis
  VIDEO_MODEL     / MULTIMODAL_MODEL    — model for video analysis
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


# ---------------------------------------------------------------------------
# Helper functions (called at module load, after dotenv is sourced)
# ---------------------------------------------------------------------------

def _int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _first_set(*keys: str, default: str = "") -> str:
    """Return the value of the first env var that is set and non-empty."""
    for key in keys:
        val = os.getenv(key, "").strip()
        if val:
            return val
    return default


# Resolve aliases at module load time so Settings fields can be plain strings.
_api_key = _first_set("GEMINI_API_KEY", "AI_API_KEY")
_provider = _first_set("AI_PROVIDER", default="mock")
_multimodal_provider = _first_set("VIDEO_PROVIDER", "MULTIMODAL_PROVIDER", "AI_PROVIDER", default="mock")
_multimodal_model = _first_set("VIDEO_MODEL", "MULTIMODAL_MODEL", default="gemini-3.7-flash")
_reasoning_model = _first_set("REASONING_MODEL", default="gemini-3.7-flash")


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("AI_HOST", "0.0.0.0")
    port: int = _int("AI_PORT", 8000)
    log_level: str = os.getenv("AI_LOG_LEVEL", "info")

    # Main reasoning provider (AI_PROVIDER in .env)
    provider: str = _provider

    # Video / multimodal provider (VIDEO_PROVIDER or MULTIMODAL_PROVIDER in .env)
    multimodal_provider: str = _multimodal_provider

    # API key: GEMINI_API_KEY takes priority over AI_API_KEY
    api_key: str = _api_key

    # Model names: VIDEO_MODEL / MULTIMODAL_MODEL aliases supported
    multimodal_model: str = _multimodal_model
    reasoning_model: str = _reasoning_model

    hf_token: str = os.getenv("HF_TOKEN", "")
    hf_model: str = os.getenv("HF_MODEL", "google/gemma-4-31B-it")
    
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1/chat/completions")

    # Cost guard rails. See docs/architecture.md#cost-aware-architecture.
    max_personas: int = _int("AI_MAX_PERSONAS", 25)
    request_timeout_seconds: int = _int("AI_REQUEST_TIMEOUT_SECONDS", 120)

    def is_configured_for(self, tier: str) -> bool:
        """True if the provider for the specified tier has credentials."""
        provider_name = self.multimodal_provider if tier == "multimodal" else self.provider
        if provider_name == "mock":
            return False
        if provider_name == "huggingface":
            return self.hf_token.strip() != ""
        if provider_name == "openai":
            return self.openai_api_key.strip() != "" or self.api_key.strip() != ""
        return self.api_key.strip() != ""

    @property
    def is_mock_mode(self) -> bool:
        """True when the main reasoning provider is unconfigured."""
        return not self.is_configured_for("reasoning")

settings = Settings()
