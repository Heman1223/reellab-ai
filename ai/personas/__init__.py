"""Persona generation and profiles. OWNER: Developer 1.

Public surface:

    generate_personas(segment, count, creator_goal) -> (list[Persona], mock)
    brief_for(persona)                              -> the persona's simulation voice
    behavioural_spread(personas)                    -> 0 (identical) .. ~1 (diverse)
    select_within_budget(personas, n)               -> trim, keeping spread
    persona_cache                                   -> process-local cache
"""

from .generation.generator import generate_personas
from .profiles.profiles import (
    PersonaCache,
    behavioural_spread,
    brief_for,
    cache_key,
    persona_cache,
    select_within_budget,
    slug_id,
)

__all__ = [
    "generate_personas",
    "PersonaCache",
    "behavioural_spread",
    "brief_for",
    "cache_key",
    "persona_cache",
    "select_within_budget",
    "slug_id",
]
