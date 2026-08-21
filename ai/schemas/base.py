"""Base model for every ReelLab contract.

Python code uses `snake_case`; the wire format is `camelCase`, matching the
TypeScript contracts in `shared/schemas/`. `populate_by_name` means both spellings
are accepted on input, so a hand-written test fixture in either style still
validates.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ReelLabModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        # Tolerate unknown fields: the TypeScript side may add an optional field
        # before the Python mirror catches up, and that must not 500 a request.
        extra="ignore",
        # `model_version` on RunMetadata would otherwise collide with pydantic's
        # reserved `model_` namespace.
        protected_namespaces=(),
    )

    def to_wire(self) -> dict:
        """Serialise with camelCase keys, ready to hand to the Node backend."""
        return self.model_dump(by_alias=True, exclude_none=True)
