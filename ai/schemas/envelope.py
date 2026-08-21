"""The response envelope every AI endpoint returns.

    { "data": <payload>, "mock": <bool>, "metadata": <RunMetadata> }

`backend/src/services/aiClient.ts` unwraps `data` and forwards `metadata` to the
observability log. `mock` is not decoration — it is how the whole team can tell,
at a glance, whether a demo is showing a model's output or a fixture.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from .simulation import RunMetadata

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    model_config = ConfigDict(protected_namespaces=())

    data: T
    mock: bool = False
    metadata: RunMetadata | None = None


def wrap(data: T, *, mock: bool, metadata: RunMetadata | None = None) -> Envelope[T]:
    return Envelope[T](data=data, mock=mock, metadata=metadata)
