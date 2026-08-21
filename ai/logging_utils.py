"""Structured JSON logging for the AI service.

Mirrors `backend/src/utils/logger.ts` field-for-field so both services' logs can
be read together. The fields that matter are the ones the brief asks us to be
able to track: model, prompt version, latency, tokens, cost, persona count.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname.lower(),
            "service": "ai",
            "msg": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update({k: v for k, v in extra.items() if v is not None})
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "info") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger("reellab")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"reellab.{name}")


def log_event(logger: logging.Logger, message: str, **fields: Any) -> None:
    """Emit one structured line. Use for anything worth counting later."""
    logger.info(message, extra={"fields": fields})
