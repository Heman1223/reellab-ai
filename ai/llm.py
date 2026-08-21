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
from errors import AINotConfiguredError, MalformedModelOutputError, ReelLabAIError, ModelTimeoutError
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

        if settings.provider == "huggingface":
            return await self._complete_huggingface(
                model=model,
                prompt=prompt,
                prompt_version=prompt_version,
                tier=tier,
                max_tokens=max_tokens,
                media_path=media_path,
                started=started,
            )
        else:
            return await self._complete_anthropic(
                model=model,
                prompt=prompt,
                prompt_version=prompt_version,
                tier=tier,
                max_tokens=max_tokens,
                media_path=media_path,
                started=started,
            )

    async def _complete_huggingface(
        self,
        *,
        model: str,
        prompt: str,
        prompt_version: str,
        tier: str,
        max_tokens: int,
        media_path: str | None,
        started: float,
    ) -> LLMResult:
        import httpx
        import json
        import base64
        from pathlib import Path

        headers = {
            "Authorization": f"Bearer {settings.hf_token}",
            "Content-Type": "application/json",
        }

        # Format messages for standard Chat Completions
        content = []
        if tier == "multimodal" and media_path:
            m_path = Path(media_path)
            if m_path.is_dir():
                frames = sorted(list(m_path.glob("*.jpg")) + list(m_path.glob("*.jpeg")))
                for f in frames:
                    with open(f, "rb") as fp:
                        encoded = base64.b64encode(fp.read()).decode("utf-8")
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                    })
        
        content.append({
            "type": "text",
            "text": prompt + "\n\nRespond ONLY with raw JSON containing the required output.",
        })

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "stream": False,
        }

        url = f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            except httpx.TimeoutException as e:
                raise ModelTimeoutError(f"Hugging Face API timed out: {str(e)}") from e
            except Exception as e:
                raise ReelLabAIError(f"Hugging Face API call failed: {str(e)}") from e

        res_json = response.json()
        try:
            raw_text = res_json["choices"][0]["message"]["content"]
            # Clean potential markdown formatting
            raw_text = raw_text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            
            data = json.loads(raw_text.strip())
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise MalformedModelOutputError(f"Model returned unparseable JSON: {str(e)}")

        if not isinstance(data, (dict, list)):
            raise MalformedModelOutputError("Model returned non-dictionary/non-list response.")

        usage_data = res_json.get("usage", {})
        metadata = self.metadata_for(
            model=model,
            prompt_version=prompt_version,
            started=started,
            usage={
                "input_tokens": usage_data.get("prompt_tokens", 0),
                "output_tokens": usage_data.get("completion_tokens", 0),
            }
        )
        return LLMResult(data=data, metadata=metadata)

    async def _complete_anthropic(
        self,
        *,
        model: str,
        prompt: str,
        prompt_version: str,
        tier: str,
        max_tokens: int,
        media_path: str | None,
        started: float,
    ) -> LLMResult:
        try:
            import anthropic  # type: ignore
        except ImportError:
            anthropic = None

        if anthropic is None:
            raise NotImplementedError("Anthropic SDK is not installed.")

        client = anthropic.AsyncAnthropic(api_key=settings.api_key)  # type: ignore
        
        content = []
        if tier == "multimodal" and media_path:
            import base64
            from pathlib import Path
            m_path = Path(media_path)
            if m_path.is_dir():
                frames = sorted(list(m_path.glob("*.jpg")) + list(m_path.glob("*.jpeg")))
                for f in frames:
                    with open(f, "rb") as fp:
                        encoded = base64.b64encode(fp.read()).decode("utf-8")
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": encoded,
                        }
                    })
                    
        content.append({
            "type": "text",
            "text": prompt
        })

        generic_tool = {
            "name": "return_json",
            "description": "Return the requested JSON structure",
            "input_schema": {
                "type": "object",
                "properties": {
                    "response": {
                        "description": "The generic JSON payload (object or array)."
                    }
                },
                "required": ["response"]
            }
        }

        try:
            res = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": content}],
                tools=[generic_tool],
                tool_choice={"type": "tool", "name": "return_json"},
            )
        except anthropic.APITimeoutError as e:  # type: ignore
            raise ModelTimeoutError(f"Anthropic API timed out: {str(e)}") from e
        except Exception as e:
            raise ReelLabAIError(f"Anthropic API call failed: {str(e)}") from e

        tool_call = next((block for block in res.content if block.type == "tool_use" and block.name == "return_json"), None)
        if not tool_call:
            raise MalformedModelOutputError("Model did not return the expected tool call.")

        data = tool_call.input.get("response")
        if data is None:
            raise MalformedModelOutputError("Model returned tool call without 'response' field.")
            
        if not isinstance(data, (dict, list)):
            raise MalformedModelOutputError("Model returned non-dictionary/non-list response.")

        metadata = self.metadata_for(
            model=model,
            prompt_version=prompt_version,
            started=started,
            usage={
                "input_tokens": getattr(res.usage, "input_tokens", 0),
                "output_tokens": getattr(res.usage, "output_tokens", 0),
            }
        )
        return LLMResult(data=data, metadata=metadata)

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
