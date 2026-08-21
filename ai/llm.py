"""The model boundary.

Every model call in ReelLab goes through this file. That is the whole point of
it: one place to add caching, batching, retries, model-tier selection and cost
accounting later, instead of eight places.

**Nothing here calls a real model yet, by design.** `complete_json` raises a
`NotImplementedError` that names the file to edit. Every AI module wraps its
call in `with_fixture_fallback`, so an unimplemented provider degrades to a
labelled fixture instead of a 500 — which is what lets four people develop in
parallel on day one.

Implementing this is the first thing Developer 1 should do.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

from config import settings
from errors import AINotConfiguredError, MalformedModelOutputError, ReelLabAIError
from logging_utils import get_logger, log_event
from schemas import RunMetadata

logger = get_logger("llm")

T = TypeVar("T")


@dataclass
class LLMResult:
    """A model response plus everything we need to account for it."""

    data: Any
    metadata: RunMetadata


class LLMClient:
    """Provider-agnostic JSON completion.

    Two tiers are exposed deliberately. The cost plan is to run most personas on
    the cheap tier and escalate only the uncertain ones — see
    docs/architecture.md#cost-aware-architecture. Nothing implements that yet,
    but the interface does not stand in its way.
    """

    def is_configured(self) -> bool:
        return not settings.is_mock_mode

    def model_for(self, tier: str) -> str:
        """`tier` is 'reasoning' (persona/bottleneck work) or 'multimodal' (video)."""
        return settings.multimodal_model if tier == "multimodal" else settings.reasoning_model

    async def complete_json(
        self,
        *,
        prompt: str,
        prompt_version: str,
        tier: str = "reasoning",
        max_tokens: int = 2048,
        media_path: str | None = None,
    ) -> LLMResult:
        """Ask a model for a JSON object.

        Raises:
            AINotConfiguredError: no provider/key set. Callers fall back to fixtures.
            NotImplementedError: provider set but the adapter is not written yet.
            MalformedModelOutputError: the model returned unparseable JSON.
        """
        if not self.is_configured():
            raise AINotConfiguredError(
                "No AI provider configured. Set AI_PROVIDER and AI_API_KEY in .env.",
                details={"provider": settings.provider},
            )

        started = time.perf_counter()
        model = self.model_for(tier)

        # ------------------------------------------------------------------
        # TODO(Developer 1): implement the provider adapter here.
        #
        # For Anthropic:
        #   1. `pip install anthropic` (uncomment it in requirements.txt)
        #   2. client = anthropic.AsyncAnthropic(api_key=settings.api_key)
        #   3. Ask for JSON via a tool definition rather than by asking nicely
        #      in the prompt — structured output that validates first time is
        #      worth far more than a retry loop.
        #   4. Parse into the caller's Pydantic model; raise
        #      MalformedModelOutputError on a validation failure so the caller
        #      can retry once with a repair prompt.
        #   5. Fill RunMetadata from the response usage block and return.
        #
        # Keep the raising branches below — an unimplemented provider must fail
        # loudly here, not silently return something plausible.
        # ------------------------------------------------------------------
        _ = (prompt, prompt_version, max_tokens, media_path, started, model)

        raise NotImplementedError(
            f"Provider '{settings.provider}' is not implemented yet. "
            "Implement LLMClient.complete_json in ai/llm.py."
        )

    @staticmethod
    def metadata_for(
        *, model: str, prompt_version: str, started: float, usage: dict | None = None
    ) -> RunMetadata:
        """Build a `RunMetadata` from a finished call. Used by the adapter above."""
        usage = usage or {}
        return RunMetadata(
            model=model,
            prompt_version=prompt_version,
            latency_ms=(time.perf_counter() - started) * 1000,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            estimated_cost_usd=usage.get("estimated_cost_usd"),
            mock=False,
        )


llm = LLMClient()


async def with_fixture_fallback(
    operation: str,
    ai_call: Callable[[], Awaitable[T]],
    fixture: Callable[[], T],
) -> tuple[T, bool]:
    """Try the model; fall back to a labelled fixture when it is not available.

    Returns `(value, mock)`.

    Only *availability* failures fall back. A `MalformedModelOutputError` is a
    real bug in a prompt and propagates — masking it with a plausible fixture is
    how a team ships a broken model and never finds out.
    """
    if settings.is_mock_mode:
        log_event(logger, "serving_fixture", operation=operation, reason="mock_mode")
        return fixture(), True

    try:
        return await ai_call(), False
    except (AINotConfiguredError, NotImplementedError) as exc:
        log_event(
            logger,
            "ai_unavailable_serving_fixture",
            operation=operation,
            reason=str(exc),
        )
        return fixture(), True
    except MalformedModelOutputError:
        raise
    except ReelLabAIError:
        raise
