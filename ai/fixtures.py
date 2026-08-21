"""Development fixtures, loaded from `data/`.

The Node backend reads the exact same files (see `backend/src/utils/fixtures.ts`),
so a fixture is a shared artefact rather than two copies that drift apart.

Anything served from here is marked `mock=True` all the way out to the browser.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from config import EVALUATION_DIR, MOCK_DIR
from schemas import (
    AudienceGraph,
    ContentDNA,
    CounterfactualExperiment,
    EvaluationDataset,
    Persona,
    RunMetadata,
    SimulationResult,
)


@lru_cache(maxsize=None)
def _read(directory_key: str, filename: str) -> str:
    directory = MOCK_DIR if directory_key == "mock" else EVALUATION_DIR
    path = directory / filename
    if not path.is_file():
        raise FileNotFoundError(
            f"Fixture '{filename}' not found at {path}. "
            "Fixtures live in data/ — see data/README.md."
        )
    return path.read_text(encoding="utf-8")


def _load(directory_key: str, filename: str) -> Any:
    return json.loads(_read(directory_key, filename))


def audience_graph() -> AudienceGraph:
    return AudienceGraph.model_validate(_load("mock", "audience_graph.json"))


def personas() -> list[Persona]:
    return [Persona.model_validate(item) for item in _load("mock", "personas.json")]


def personas_for_segment(segment_id: str, count: int | None = None) -> list[Persona]:
    matches = [persona for persona in personas() if persona.segment_id == segment_id]
    # Fall back to the full pool so a newly invented segment id still gets
    # something to work with rather than an empty simulation.
    pool = matches or personas()
    return pool[:count] if count else pool


def content_dna() -> ContentDNA:
    return ContentDNA.model_validate(_load("mock", "content_dna.json"))


def simulation_result() -> SimulationResult:
    return SimulationResult.model_validate(_load("mock", "simulation_result.json"))


def counterfactual_experiment() -> CounterfactualExperiment:
    return CounterfactualExperiment.model_validate(
        _load("mock", "counterfactual_experiment.json")
    )


def evaluation_dataset() -> EvaluationDataset:
    return EvaluationDataset.model_validate(_load("evaluation", "historical_reels.json"))


def mock_metadata(**overrides: Any) -> RunMetadata:
    """Metadata stamped on every fixture-backed response."""
    base = {"model": "fixture", "prompt_version": "n/a", "latency_ms": 0.0, "mock": True}
    base.update(overrides)
    return RunMetadata.model_validate(base)
