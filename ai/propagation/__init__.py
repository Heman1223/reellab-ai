"""Propagation cascade mechanics. OWNER: Developer 1.

Public surface:

    simulate_propagation(persona_results, seed=42) -> list[PropagationWave]

Deterministic for a given seed. Optional `graph`, `segment_results` and
`personas` keywords enable cross-segment spillover.
"""

from .engine.propagation import (
    AMPLIFICATION,
    MAX_WAVES,
    MIN_REACH,
    SEED_REACH,
    simulate_propagation,
)

__all__ = [
    "AMPLIFICATION",
    "MAX_WAVES",
    "MIN_REACH",
    "SEED_REACH",
    "simulate_propagation",
]
