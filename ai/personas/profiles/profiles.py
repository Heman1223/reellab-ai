"""Persona profile utilities.

Deterministic helpers for working with generated personas: caching keys,
selection under a budget, and the brief handed to the simulation model.

No model calls here.

OWNER: Developer 1.
"""

from __future__ import annotations

import hashlib

from schemas import Persona


def cache_key(segment_id: str, count: int, prompt_version: str) -> str:
    """Stable key for reusing personas instead of regenerating them.

    Persona generation is the second-largest cost in a run after simulation
    itself, and personas for an unchanged segment do not need to be reinvented.
    Nothing reads this yet — it is here so caching stays a small change rather
    than a refactor.
    """
    raw = f"{segment_id}:{count}:{prompt_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


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


def select_within_budget(personas: list[Persona], max_personas: int) -> list[Persona]:
    """Trim a persona set to a budget, keeping behavioural spread.

    Sorts by swipe tendency and samples evenly across the range, so a trimmed
    run keeps both the impatient and the patient viewers. Dropping the tail
    would make every trimmed simulation look better than the real audience.
    """
    if len(personas) <= max_personas:
        return personas

    ordered = sorted(personas, key=lambda p: p.attention_profile.swipe_tendency)
    step = len(ordered) / max_personas
    return [ordered[int(index * step)] for index in range(max_personas)]
