"""Persona profile utilities: ids, briefs, diversity, budget selection, caching.

Deterministic helpers only — no model calls here.

OWNER: Developer 1.
"""

from __future__ import annotations

import hashlib
import re
from statistics import mean, pstdev

from schemas import Persona

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slug_id(segment_id: str, name: str, index: int) -> str:
    """Stable persona id: segment + name + position.

    Deterministic rather than a UUID so that regenerating the same segment
    produces the same ids, which is what makes persona caching and run-to-run
    comparison possible.
    """
    cleaned = _SLUG_STRIP.sub("_", name.strip().lower()).strip("_") or "persona"
    return f"{segment_id}__{cleaned[:24]}_{index}"


def cache_key(segment_id: str, count: int, prompt_version: str) -> str:
    """Key for reusing personas instead of regenerating them.

    Includes the prompt version so improving the prompt invalidates the cache
    rather than silently serving personas from an older, worse one.
    """
    raw = f"{segment_id}:{count}:{prompt_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class PersonaCache:
    """Process-local persona cache.

    Deliberately trivial: a dict with a size cap. Persona generation is
    expensive and personas for an unchanged segment do not need reinventing, but
    a real cache (Redis, Mongo) is Developer 4's call and a later decision. This
    keeps the call site correct in the meantime — swapping the implementation
    means changing this class and nothing else.

    Not persisted; a restart regenerates.
    """

    def __init__(self, max_entries: int = 128) -> None:
        self._entries: dict[str, list[Persona]] = {}
        self._max_entries = max_entries

    def get(self, key: str) -> list[Persona] | None:
        return self._entries.get(key)

    def put(self, key: str, personas: list[Persona]) -> None:
        if len(self._entries) >= self._max_entries:
            # Cheapest eviction that cannot grow unbounded. Insertion-ordered.
            self._entries.pop(next(iter(self._entries)))
        self._entries[key] = personas

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)


persona_cache = PersonaCache()


def brief_for(persona: Persona) -> str:
    """The text handed to the model when this persona watches a reel.

    Falls back to assembling one from the structured fields when the generator
    did not supply a `system_brief`.
    """
    if persona.system_brief:
        return persona.system_brief

    attention = persona.attention_profile
    triggers = ", ".join(attention.drop_off_triggers) or "nothing in particular"

    return (
        f"You are {persona.name}. {persona.demographic_summary}. "
        f"You are interested in {', '.join(persona.interests) or 'very little'}. "
        f"You typically give a video about {attention.average_attention_seconds:.0f} seconds "
        f"before deciding. You swipe away because of: {triggers}."
    )


def behavioural_spread(personas: list[Persona]) -> float:
    """How differently this set of personas behaves, 0 (identical) .. ~1.

    Population standard deviation across the traits that decide an outcome,
    averaged. Used to catch a generation that produced five names for one
    person — which would make the simulation look far more certain than it is.
    """
    if len(personas) < 2:
        return 0.0

    axes = [
        [p.attention_profile.swipe_tendency for p in personas],
        [p.engagement_profile.share_tendency for p in personas],
        [p.engagement_profile.save_tendency for p in personas],
        [min(1.0, p.attention_profile.average_attention_seconds / 15.0) for p in personas],
    ]
    return round(mean(pstdev(axis) for axis in axes), 4)


def select_within_budget(personas: list[Persona], max_personas: int) -> list[Persona]:
    """Trim a persona set to a budget, keeping behavioural spread.

    Sorts by swipe tendency and samples evenly across the range, so a trimmed
    run keeps both the impatient and the patient viewers. Dropping the tail
    would make every trimmed simulation look better than the real audience.
    """
    if max_personas <= 0:
        return []
    if len(personas) <= max_personas:
        return personas

    ordered = sorted(personas, key=lambda p: p.attention_profile.swipe_tendency)
    step = len(ordered) / max_personas
    return [ordered[int(index * step)] for index in range(max_personas)]
