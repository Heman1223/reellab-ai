"""The model boundary.

Every model call in ReelLab goes through this file. One place to add caching,
batching, retries, model-tier selection and cost accounting — instead of eight.

OWNER: Developer 1 (see docs/development-workflow.md).

**Compatibility contract.** Developer 2's `video_analysis/multimodal/analyzer.py`
and `counterfactual/generation/variants.py` both import `llm` and
`with_fixture_fallback` from here and call `llm.complete_json(prompt=...,
prompt_version=..., tier=..., max_tokens=..., media_path=...)`. Those signatures
are frozen — do not change them without telling Developer 2.

Providers talk raw HTTP over `httpx` rather than through vendor SDKs. That keeps
`requirements.txt` untouched (httpx is already a dependency), and it makes
swapping providers a matter of adding one small class rather than a dependency
negotiation mid-hackathon.
"""

from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from config import settings
from errors import (
    AINotConfiguredError,
    MalformedModelOutputError,
    ModelTimeoutError,
    ReelLabAIError,
)
from logging_utils import get_logger, log_event
from schemas import RunMetadata

logger = get_logger("llm")

T = TypeVar("T")
ModelT = TypeVar("ModelT", bound=BaseModel)


def _int_env(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


#: How many times to re-ask after a malformed response, per call.
MAX_RETRIES = _int_env("AI_MAX_RETRIES", 1)

#: Tokens Gemini may spend on internal reasoning before answering. 0 disables
#: thinking entirely, which is roughly 10x cheaper — measured at 325 thinking
#: tokens against 36 output tokens on a trivial prompt.
#:
#: This is NOT free budget: Gemini counts thinking against `maxOutputTokens`, so
#: the adapter adds it on top of the caller's limit rather than letting it eat
#: the answer. See `GeminiProvider.generate_structured`.
THINKING_BUDGET = _int_env("AI_THINKING_BUDGET", 512)

#: Attempts against a busy provider, and the base delay between them (doubling
#: each time): 2s, 4s, 8s. Gemini returns intermittent 503s on large prompts
#: even when small ones succeed, and a one-second retry is not enough to clear
#: them. Four attempts caps the wait at ~14s before a persona is given up on.
OVERLOAD_ATTEMPTS = _int_env("AI_OVERLOAD_ATTEMPTS", 4)
OVERLOAD_BACKOFF_SECONDS = float(os.getenv("AI_OVERLOAD_BACKOFF_SECONDS", "2.0"))

#: **Approximate** USD per 1M tokens, for the cost figure in logs only.
#: Anthropic and OpenAI rates are ballpark; the Gemini 3.x rates are estimates
#: that have NOT been checked against a pricing page. Verify before quoting any
#: of these to anyone. Longest matching prefix wins.
APPROX_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus": (5.00, 25.00),
    "claude-sonnet": (3.00, 15.00),
    "claude-haiku": (1.00, 5.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gemini-3.1-pro": (1.25, 10.00),
    "gemini-3": (0.30, 2.50),
    "gemini-2": (0.30, 2.50),
}


def estimate_cost_usd(model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    """Rough spend for one call. `None` when the model is not in the table.

    `output_tokens` should already include any thinking tokens — providers bill
    for those, so excluding them would under-report what a run costs.
    """
    if input_tokens is None and output_tokens is None:
        return None

    # Longest prefix first, so "gemini-3.1-pro" beats "gemini-3".
    for prefix in sorted(APPROX_PRICING, key=len, reverse=True):
        if model.startswith(prefix):
            in_rate, out_rate = APPROX_PRICING[prefix]
            return round(
                ((input_tokens or 0) / 1_000_000) * in_rate
                + ((output_tokens or 0) / 1_000_000) * out_rate,
                6,
            )
    return None


# ---------------------------------------------------------------------------
# JSON Schema helpers
# ---------------------------------------------------------------------------

def _dereference(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline every `$ref` so nested models survive the trip to a provider.

    Pydantic emits `$defs` + `$ref` for nested models. Provider schema validators
    disagree about how much of that they support, and a rejected schema is a
    confusing 400 rather than a useful error. Inlining sidesteps the whole
    argument.

    Recursive models would loop forever here; ReelLab has none, and the depth
    guard turns that mistake into a clear failure instead of a hang.
    """
    defs = schema.get("$defs", {})

    def resolve(node: Any, depth: int = 0) -> Any:
        if depth > 12:
            raise ReelLabAIError("Schema nesting too deep to inline; is a model recursive?")
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                name = ref.rsplit("/", 1)[-1]
                target = defs.get(name)
                if target is None:
                    return {"type": "object"}
                merged = {k: v for k, v in node.items() if k != "$ref"}
                return {**resolve(target, depth + 1), **merged}
            return {key: resolve(value, depth + 1) for key, value in node.items() if key != "$defs"}
        if isinstance(node, list):
            return [resolve(item, depth + 1) for item in node]
        return node

    resolved = resolve(schema)
    resolved.pop("$defs", None)
    return resolved


def schema_for(model_cls: type[BaseModel]) -> dict[str, Any]:
    """JSON Schema for a Pydantic model, with refs inlined and aliases applied.

    `by_alias=True` matters: the model must be told to emit `watchProbability`,
    not `watch_probability`.
    """
    return _dereference(model_cls.model_json_schema(by_alias=True))


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

@dataclass
class MediaAttachment:
    """An image handed to a multimodal model."""

    media_type: str
    data_b64: str

    @classmethod
    def from_path(cls, path: str | Path) -> "MediaAttachment | None":
        """Read an image file. Returns `None` for anything that is not an image.

        Video paths are deliberately not attachable — Developer 2's pipeline
        extracts frames and passes those. Silently uploading a 100 MB MP4 would
        be an expensive surprise.
        """
        file_path = Path(path)
        if not file_path.is_file():
            return None

        media_type = mimetypes.guess_type(file_path.name)[0] or ""
        if not media_type.startswith("image/"):
            return None

        return cls(
            media_type=media_type,
            data_b64=base64.b64encode(file_path.read_bytes()).decode("ascii"),
        )


@dataclass
class ProviderResponse:
    """What a provider gives back, normalised across vendors."""

    data: Any
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw_text: str = ""


class ModelProvider(Protocol):
    """Minimal provider interface.

    One method. Adding Gemini, a local model or a fallback means writing a class
    with this shape and registering it in `PROVIDERS` — not touching any caller.
    """

    name: str

    async def generate_structured(
        self,
        *,
        prompt: str,
        system: str,
        schema: dict[str, Any],
        model: str,
        max_tokens: int,
        timeout: float,
        media: list[MediaAttachment],
    ) -> ProviderResponse: ...


def _parse_json(text: str) -> Any:
    """Parse a JSON body, tolerating the fences models like to add."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1] if "```" in cleaned[3:] else cleaned[3:]
        if cleaned.lstrip().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError as exc:
        raise MalformedModelOutputError(
            f"Model did not return valid JSON: {exc}",
            details={"snippet": text[:300]},
        ) from exc


class AnthropicProvider:
    """Anthropic Messages API.

    Structured output is forced through a single-tool `tool_choice` rather than
    asked for in the prompt. Asking nicely produces prose about JSON often
    enough to matter when you are making one call per persona.
    """

    name = "anthropic"
    endpoint = "https://api.anthropic.com/v1/messages"
    version = "2023-06-01"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def generate_structured(
        self,
        *,
        prompt: str,
        system: str,
        schema: dict[str, Any],
        model: str,
        max_tokens: int,
        timeout: float,
        media: list[MediaAttachment],
    ) -> ProviderResponse:
        content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": item.media_type,
                    "data": item.data_b64,
                },
            }
            for item in media
        ]
        content.append({"type": "text", "text": prompt})

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": content}],
            "tools": [
                {
                    "name": "emit_result",
                    "description": "Return the result as structured data.",
                    "input_schema": schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": "emit_result"},
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self.endpoint,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": self.version,
                    "content-type": "application/json",
                },
                json=payload,
            )

        _raise_for_status(response, self.name)
        body = response.json()

        for block in body.get("content", []):
            if block.get("type") == "tool_use":
                usage = body.get("usage", {})
                return ProviderResponse(
                    data=block.get("input"),
                    model=body.get("model", model),
                    input_tokens=usage.get("input_tokens"),
                    output_tokens=usage.get("output_tokens"),
                )

        raise MalformedModelOutputError(
            "Anthropic returned no tool_use block.",
            details={"stop_reason": body.get("stop_reason")},
        )


class OpenAIProvider:
    """OpenAI Chat Completions with a strict JSON schema response format."""

    name = "openai"
    endpoint = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def generate_structured(
        self,
        *,
        prompt: str,
        system: str,
        schema: dict[str, Any],
        model: str,
        max_tokens: int,
        timeout: float,
        media: list[MediaAttachment],
    ) -> ProviderResponse:
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        content.extend(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{item.media_type};base64,{item.data_b64}"},
            }
            for item in media
        )

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "result", "schema": schema, "strict": False},
            },
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        _raise_for_status(response, self.name)
        body = response.json()

        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise MalformedModelOutputError("OpenAI returned no message content.") from exc

        usage = body.get("usage", {})
        return ProviderResponse(
            data=_parse_json(text),
            model=body.get("model", model),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw_text=text,
        )


def _gemini_text(candidate: dict[str, Any]) -> str:
    """Join the answer parts, skipping the model's internal thought parts.

    With thinking enabled a candidate can carry thought parts alongside the
    answer. Reading `parts[0]["text"]` blindly returns a thought fragment — or
    raises, because a thought part need not have a `text` key at all.
    """
    parts = candidate.get("content", {}).get("parts") or []
    return "".join(
        part["text"]
        for part in parts
        if isinstance(part, dict) and not part.get("thought") and isinstance(part.get("text"), str)
    )


class GeminiProvider:
    """Google Gemini via the generative language REST API.

    Two behaviours here are Gemini-specific and were found by running against
    the live API rather than by reading the docs:

    1. **Thinking tokens count against `maxOutputTokens`.** Ask for 60 tokens on
       a thinking model and you get 55 tokens of thought, one token of answer,
       and `finishReason: MAX_TOKENS`. So the thinking budget is added on top of
       the caller's limit — `max_tokens` means answer tokens, as callers expect.
    2. **There is no server-side schema enforcement in JSON mode.** Gemini's
       `responseSchema` accepts a narrower dialect than Pydantic emits (our
       optional fields become `anyOf`, which it rejects), so the schema is
       appended to the prompt instead and `complete_model` validates the result.
    """

    name = "gemini"
    base = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, thinking_budget: int | None = None) -> None:
        self._api_key = api_key
        self._thinking_budget = THINKING_BUDGET if thinking_budget is None else thinking_budget

    async def generate_structured(
        self,
        *,
        prompt: str,
        system: str,
        schema: dict[str, Any],
        model: str,
        max_tokens: int,
        timeout: float,
        media: list[MediaAttachment],
    ) -> ProviderResponse:
        instructions = prompt
        if schema and schema.get("properties"):
            instructions = (
                f"{prompt}\n\nReturn a single JSON object matching this JSON Schema "
                f"exactly. Use these key names verbatim:\n{json.dumps(schema)}"
            )

        parts: list[dict[str, Any]] = [{"text": instructions}]
        parts.extend(
            {"inline_data": {"mime_type": item.media_type, "data": item.data_b64}}
            for item in media
        )

        budget = max(0, self._thinking_budget)
        generation_config: dict[str, Any] = {
            # Thinking is billed out of this same allowance, so add it on top.
            "maxOutputTokens": max_tokens + budget,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": budget},
        }

        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": generation_config,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base}/{model}:generateContent",
                headers={"Content-Type": "application/json", "x-goog-api-key": self._api_key},
                json=payload,
            )

        _raise_for_status(response, self.name)
        body = response.json()

        candidates = body.get("candidates") or []
        if not candidates:
            raise MalformedModelOutputError(
                "Gemini returned no candidates.",
                details={"promptFeedback": body.get("promptFeedback")},
            )

        candidate = candidates[0]
        finish = candidate.get("finishReason")
        text = _gemini_text(candidate)

        if finish == "MAX_TOKENS" and not text.strip():
            raise MalformedModelOutputError(
                "Gemini hit the output limit before answering — the thinking budget "
                "consumed the whole allowance. Raise max_tokens or lower "
                "AI_THINKING_BUDGET.",
                details={"maxOutputTokens": generation_config["maxOutputTokens"]},
            )
        if not text.strip():
            raise MalformedModelOutputError(
                "Gemini returned no answer text.",
                details={"finishReason": finish},
            )

        usage = body.get("usageMetadata", {})
        # Thinking tokens are billed as output, so fold them in or the cost
        # figure understates a thinking run by roughly an order of magnitude.
        output_tokens = (usage.get("candidatesTokenCount") or 0) + (
            usage.get("thoughtsTokenCount") or 0
        )

        return ProviderResponse(
            data=_parse_json(text),
            model=model,
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=output_tokens or None,
            raw_text=text,
        )


class ProviderOverloadedError(ReelLabAIError):
    """Temporarily unavailable — worth retrying with backoff.

    Nothing is wrong with the prompt, the provider is just busy. Gemini returns
    503 "experiencing high demand" fairly readily on large prompts even while
    small ones succeed, and a demo that dies on one transient 503 is a demo that
    dies.
    """

    code = "AI_PROVIDER_OVERLOADED"
    http_status = 503


class QuotaExhaustedError(ReelLabAIError):
    """The key is out of quota. Retrying will not help.

    Treated as an *availability* failure, not an error: it is in
    `AVAILABILITY_ERRORS`, so callers degrade to a clearly-labelled fixture
    rather than failing the run. This is the mock-first architecture doing
    exactly the job it was built for.

    Worth knowing: Gemini's free tier is **20 requests per day, per model, per
    project**. One standard simulation is roughly 22 calls, so a free key is
    exhausted by a single run. See docs/failure-log.md.
    """

    code = "AI_QUOTA_EXHAUSTED"
    http_status = 429


#: Transient statuses worth another attempt. 429 is handled separately because
#: a exhausted daily quota is not something backoff can fix.
RETRYABLE_STATUS = {500, 502, 503, 529}


def _retry_delay(body: dict[str, Any]) -> float | None:
    """Seconds the provider asked us to wait, from a google.rpc.RetryInfo block."""
    for detail in body.get("error", {}).get("details", []) or []:
        if isinstance(detail, dict) and detail.get("@type", "").endswith("RetryInfo"):
            raw = str(detail.get("retryDelay", "")).rstrip("s")
            try:
                return float(raw)
            except ValueError:
                return None
    return None


def _raise_for_status(response: httpx.Response, provider: str) -> None:
    """Translate an HTTP failure into one of our typed errors."""
    if response.status_code < 400:
        return

    snippet = response.text[:300]

    if response.status_code in (401, 403):
        raise AINotConfiguredError(
            f"{provider} rejected the API key.",
            details={"status": response.status_code},
        )
    if response.status_code in (408, 504):
        raise ModelTimeoutError(f"{provider} timed out.", details={"body": snippet})

    if response.status_code == 429:
        try:
            body = response.json()
        except ValueError:
            body = {}
        raise QuotaExhaustedError(
            f"{provider} quota exhausted. Falling back to fixtures.",
            details={
                "retryAfterSeconds": _retry_delay(body),
                "message": body.get("error", {}).get("message", snippet)[:300],
            },
        )

    if response.status_code in RETRYABLE_STATUS:
        raise ProviderOverloadedError(
            f"{provider} is busy (HTTP {response.status_code}).",
            details={"status": response.status_code, "body": snippet},
        )

    raise ReelLabAIError(
        f"{provider} returned {response.status_code}.",
        details={"body": snippet},
    )


class HuggingFaceProvider:
    """HuggingFace Inference API via the Chat Completions endpoint.

    Supports multimodal inputs (image frames) by base64-encoding JPEG files
    from a directory path. The model is expected to return raw JSON.
    """

    name = "huggingface"

    def __init__(self, api_key: str) -> None:
        # api_key is the HF_TOKEN for HuggingFace
        self._api_key = api_key

    async def generate_structured(
        self,
        *,
        prompt: str,
        system: str,
        schema: dict[str, Any],
        model: str,
        max_tokens: int,
        timeout: float,
        media: list[MediaAttachment],
    ) -> ProviderResponse:
        content: list[dict[str, Any]] = []
        for item in media:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{item.media_type};base64,{item.data_b64}"},
                }
            )
        content.append(
            {
                "type": "text",
                "text": prompt + "\n\nRespond ONLY with raw JSON containing the required output.",
            }
        )

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "stream": False,
        }

        url = f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        _raise_for_status(response, self.name)
        body = response.json()

        try:
            raw_text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise MalformedModelOutputError("HuggingFace returned no message content.") from exc

        usage = body.get("usage", {})
        return ProviderResponse(
            data=_parse_json(raw_text),
            model=model,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw_text=raw_text,
        )


PROVIDERS: dict[str, Callable[[str], ModelProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "huggingface": HuggingFaceProvider,
}


# ---------------------------------------------------------------------------
# Client facade
# ---------------------------------------------------------------------------

@dataclass
class LLMResult:
    """A model response plus everything we need to account for it."""

    data: Any
    metadata: RunMetadata


@dataclass
class CallStats:
    """Process-lifetime call counters, for cost visibility during a run."""

    calls: int = 0
    failures: int = 0
    retries: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def snapshot(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "failures": self.failures,
            "retries": self.retries,
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "estimatedCostUsd": round(self.estimated_cost_usd, 6),
        }


SYSTEM_PROMPT = (
    "You are a component inside ReelLab, a synthetic audience simulator for "
    "short-form video creators. You return structured data only. Be specific and "
    "concrete; vague output is worse than no output. When you are unsure, say so "
    "through the confidence fields rather than by hedging the wording."
)


class LLMClient:
    """Provider-agnostic structured generation.

    Two tiers are exposed deliberately: `multimodal` for anything involving
    frames, `reasoning` for persona and analysis work. The eventual cost plan is
    to run easy personas on a cheap tier and escalate only uncertain ones —
    `model_for` is the seam for that.
    """

    def __init__(self) -> None:
        self.stats = CallStats()

    # -- configuration ----------------------------------------------------

    def is_configured(self, tier: str = "reasoning") -> bool:
        provider_name = settings.multimodal_provider if tier == "multimodal" else settings.provider
        return settings.is_configured_for(tier) and provider_name in PROVIDERS

    def provider_for(self, tier: str) -> ModelProvider:
        provider_name = settings.multimodal_provider if tier == "multimodal" else settings.provider
        factory = PROVIDERS.get(provider_name)
        if factory is None:
            config_key = "MULTIMODAL_PROVIDER" if tier == "multimodal" else "AI_PROVIDER"
            raise AINotConfiguredError(
                f"Unknown {config_key} '{provider_name}'. "
                f"Expected one of: {', '.join(sorted(PROVIDERS))}, or 'mock'.",
            )
        if provider_name == "huggingface":
            token = settings.hf_token
            if not token.strip():
                raise AINotConfiguredError("HF_TOKEN is empty (required for huggingface provider).")
            return factory(token)
        if not settings.api_key.strip():
            raise AINotConfiguredError("AI_API_KEY is empty.")
        return factory(settings.api_key)

    def model_for(self, tier: str) -> str:
        return settings.multimodal_model if tier == "multimodal" else settings.reasoning_model

    # -- generation -------------------------------------------------------

    async def complete_model(
        self,
        model_cls: type[ModelT],
        *,
        prompt: str,
        prompt_version: str,
        tier: str = "reasoning",
        max_tokens: int = 2048,
        media: list[MediaAttachment] | None = None,
        system: str = SYSTEM_PROMPT,
        max_retries: int | None = None,
    ) -> tuple[ModelT, RunMetadata]:
        """Generate and **validate** against a Pydantic model.

        This is the entry point simulation code should use. Validation is the
        point: a model that returns `shareProbability: 1.4` is caught here, not
        three layers later when a segment score comes out above 1.

        On a malformed or invalid response it retries once (configurable) with
        the validation errors appended to the prompt, which repairs most
        first-attempt failures. After that it raises
        `MalformedModelOutputError` and the caller decides what to do — for a
        persona, that means marking one persona failed and continuing.
        """
        attempts = (max_retries if max_retries is not None else MAX_RETRIES) + 1
        schema = schema_for(model_cls)
        current_prompt = prompt
        started = time.perf_counter()
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                response = await self._call_provider(
                    prompt=current_prompt,
                    system=system,
                    schema=schema,
                    tier=tier,
                    max_tokens=max_tokens,
                    media=media or [],
                )
                validated = model_cls.model_validate(response.data)
                metadata = self._record(response, prompt_version, started)
                return validated, metadata

            except ValidationError as exc:
                last_error = exc
                current_prompt = (
                    f"{prompt}\n\n"
                    "Your previous response failed validation. Fix exactly these "
                    f"problems and return the corrected JSON:\n{exc.errors()[:8]}"
                )
            except MalformedModelOutputError as exc:
                last_error = exc
                current_prompt = (
                    f"{prompt}\n\nYour previous response was not valid JSON. "
                    "Return a single JSON object and nothing else."
                )

            if attempt + 1 < attempts:
                self.stats.retries += 1
                log_event(
                    logger,
                    "model_output_retry",
                    prompt_version=prompt_version,
                    attempt=attempt + 1,
                    error=str(last_error)[:200],
                )

        self.stats.failures += 1
        raise MalformedModelOutputError(
            f"Model output failed validation after {attempts} attempt(s).",
            details={"promptVersion": prompt_version, "error": str(last_error)[:500]},
        )

    async def complete_json(
        self,
        *,
        prompt: str,
        prompt_version: str,
        tier: str = "reasoning",
        max_tokens: int = 2048,
        media_path: str | None = None,
        schema: dict[str, Any] | None = None,
        system: str = SYSTEM_PROMPT,
    ) -> LLMResult:
        """Unvalidated JSON generation.

        Kept for Developer 2's existing call sites, whose signature this must
        not change. Prefer `complete_model` in new code — it validates.
        """
        media: list[MediaAttachment] = []
        if media_path:
            attachment = MediaAttachment.from_path(media_path)
            if attachment:
                media.append(attachment)

        started = time.perf_counter()
        response = await self._call_provider(
            prompt=prompt,
            system=system,
            schema=schema or {"type": "object"},
            tier=tier,
            max_tokens=max_tokens,
            media=media,
        )
        return LLMResult(data=response.data, metadata=self._record(response, prompt_version, started))

    # -- internals --------------------------------------------------------

    async def _call_provider(
        self,
        *,
        prompt: str,
        system: str,
        schema: dict[str, Any],
        tier: str,
        max_tokens: int,
        media: list[MediaAttachment],
    ) -> ProviderResponse:
        if not self.is_configured(tier):
            config_key = "MULTIMODAL_PROVIDER" if tier == "multimodal" else "AI_PROVIDER"
            provider_name = settings.multimodal_provider if tier == "multimodal" else settings.provider
            raise AINotConfiguredError(
                f"No AI provider configured for tier '{tier}'. Set {config_key} and corresponding API keys in .env.",
                details={"provider": provider_name, "tier": tier},
            )

        provider = self.provider_for(tier)
        model = self.model_for(tier)
        last: Exception | None = None

        # Transient failures get a few attempts with exponential backoff. This
        # is separate from the malformed-output retry in `complete_model`:
        # nothing is wrong with the prompt here, the provider is just busy.
        for attempt in range(OVERLOAD_ATTEMPTS):
            try:
                return await provider.generate_structured(
                    prompt=prompt,
                    system=system,
                    schema=schema,
                    model=model,
                    max_tokens=max_tokens,
                    timeout=float(settings.request_timeout_seconds),
                    media=media,
                )
            except ProviderOverloadedError as exc:
                last = exc
                if attempt + 1 < OVERLOAD_ATTEMPTS:
                    delay = OVERLOAD_BACKOFF_SECONDS * (2**attempt)
                    log_event(
                        logger,
                        "provider_overloaded_retrying",
                        provider=provider.name,
                        attempt=attempt + 1,
                        delay_seconds=delay,
                    )
                    await asyncio.sleep(delay)
            except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
                self.stats.failures += 1
                raise ModelTimeoutError(
                    f"{provider.name} did not respond within "
                    f"{settings.request_timeout_seconds}s.",
                ) from exc
            except httpx.HTTPError as exc:
                self.stats.failures += 1
                raise ReelLabAIError(f"Could not reach {provider.name}: {exc}") from exc

        self.stats.failures += 1
        raise last or ReelLabAIError(f"{provider.name} was unreachable.")

    def _record(
        self, response: ProviderResponse, prompt_version: str, started: float
    ) -> RunMetadata:
        latency_ms = (time.perf_counter() - started) * 1000
        cost = estimate_cost_usd(response.model, response.input_tokens, response.output_tokens)

        self.stats.calls += 1
        self.stats.input_tokens += response.input_tokens or 0
        self.stats.output_tokens += response.output_tokens or 0
        self.stats.estimated_cost_usd += cost or 0.0

        metadata = RunMetadata(
            model=response.model,
            prompt_version=prompt_version,
            latency_ms=round(latency_ms, 2),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            estimated_cost_usd=cost,
            mock=False,
        )

        log_event(
            logger,
            "model_call",
            provider=settings.provider,
            model=response.model,
            prompt_version=prompt_version,
            latency_ms=metadata.latency_ms,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            estimated_cost_usd=cost,
        )
        return metadata


llm = LLMClient()


# ---------------------------------------------------------------------------
# Mock-first execution
# ---------------------------------------------------------------------------

#: Failures that mean "the model was not available", as opposed to "the model
#: was available and got it wrong". Quota exhaustion belongs here: no amount of
#: retrying fixes a daily limit, and a labelled fixture beats a dead run.
AVAILABILITY_ERRORS = (AINotConfiguredError, NotImplementedError, QuotaExhaustedError)


async def with_fixture_fallback(
    operation: str,
    ai_call: Callable[[], Awaitable[T]],
    fixture: Callable[[], T],
) -> tuple[T, bool]:
    """Try the model; fall back to a labelled fixture when it is unavailable.

    Returns `(value, mock)`.

    Only *availability* failures fall back. A `MalformedModelOutputError` is a
    real bug in a prompt and propagates — masking it with a plausible fixture is
    how a team ships a broken model and never finds out.

    Signature is frozen: Developer 2 calls this from two modules.
    """
    if settings.is_mock_mode:
        log_event(logger, "serving_fixture", operation=operation, reason="mock_mode")
        return fixture(), True

    try:
        return await ai_call(), False
    except AVAILABILITY_ERRORS as exc:
        log_event(logger, "ai_unavailable_serving_fixture", operation=operation, reason=str(exc)[:200])
        return fixture(), True
    except MalformedModelOutputError:
        raise
    except ReelLabAIError:
        raise
