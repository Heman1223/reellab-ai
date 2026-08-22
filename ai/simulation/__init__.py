"""Persona simulation and the run engine. OWNER: Developer 1.

Public surface:

    simulate_persona(persona, content)                 -> (PersonaSimulationResult, mock)
    run_simulation_for_personas(personas, content, ..) -> (SimulationResult, mock)
    run_simulation(request, content?, graph?)          -> (SimulationResult, mock)
    SimulationOptions                                  -> depth / budget / seed / concurrency
    analyze_bottlenecks(...)                           -> (list[Bottleneck], mock)
    compute_confidence(...)                            -> ConfidenceBreakdown

`run_simulation` takes a `SimulationRequest` and resolves the audience itself.
`run_simulation_for_personas` is the core for callers that already have personas.
"""

from .agents.viewer_agent import failed_result, simulate_persona
from .behavior.aggregation import (
    AudienceAnalysis,
    ConfidenceBreakdown,
    aggregate_segment,
    analyse_audience,
    compute_confidence,
    content_gaps,
    disagreement,
    overall_score,
    segment_score,
    usable,
    verdict_for,
)
from .behavior.reflection import analyze_bottlenecks, detect_signals
from .engine.engine import (
    SimulationOptions,
    run_simulation,
    run_simulation_for_personas,
)

__all__ = [
    "simulate_persona",
    "failed_result",
    "run_simulation",
    "run_simulation_for_personas",
    "SimulationOptions",
    "aggregate_segment",
    "analyse_audience",
    "AudienceAnalysis",
    "compute_confidence",
    "ConfidenceBreakdown",
    "content_gaps",
    "disagreement",
    "overall_score",
    "segment_score",
    "usable",
    "verdict_for",
    "analyze_bottlenecks",
    "detect_signals",
]
