"""Contract tests.

These are the tests that catch schema drift between `ai/schemas/` (Pydantic) and
`shared/schemas/` (TypeScript). The fixtures in `data/` are written in the
TypeScript camelCase spelling, so if a Pydantic model has drifted, validating a
fixture against it fails here — before it fails in someone's browser.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import fixtures
from schemas import (
    AudienceGraph,
    AudienceRequest,
    ContentDNA,
    CounterfactualExperiment,
    Persona,
    RunMetadata,
    SimulationResult,
)


def test_every_fixture_validates_against_its_schema():
    assert isinstance(fixtures.audience_graph(), AudienceGraph)
    assert isinstance(fixtures.content_dna(), ContentDNA)
    assert isinstance(fixtures.simulation_result(), SimulationResult)
    assert isinstance(fixtures.counterfactual_experiment(), CounterfactualExperiment)
    assert all(isinstance(persona, Persona) for persona in fixtures.personas())


def test_fixture_counts_match_the_brief():
    assert len(fixtures.audience_graph().segments) >= 3
    assert len(fixtures.personas()) >= 5


def test_wire_format_is_camel_case():
    """The Node backend and the browser only ever see camelCase."""
    wire = fixtures.content_dna().to_wire()

    assert "videoId" in wire
    assert "durationSeconds" in wire
    assert "visualFeatures" in wire
    assert "video_id" not in wire


def test_snake_case_input_is_also_accepted():
    """`populate_by_name` keeps hand-written Python fixtures usable."""
    request = AudienceRequest(
        niche="fitness",
        target_audience="beginners",
        location="India",
        language="English",
        creator_goal="reach",
    )
    assert request.target_audience == "beginners"
    assert request.to_wire()["targetAudience"] == "beginners"


def test_probabilities_are_bounded():
    with pytest.raises(ValidationError):
        fixtures.simulation_result().model_copy(
            update={"overall_score": 1.7}
        ).model_validate(
            {**fixtures.simulation_result().model_dump(), "overall_score": 1.7}
        )


def test_run_metadata_allows_a_model_version_field():
    """`model_version` collides with pydantic's reserved namespace unless configured."""
    metadata = RunMetadata(model="claude-opus-5", model_version="2026-05", mock=False)
    assert metadata.to_wire()["modelVersion"] == "2026-05"


def test_fixtures_are_internally_consistent():
    """Ids must join up, or the frontend renders a dashboard full of holes."""
    graph = fixtures.audience_graph()
    personas = fixtures.personas()
    simulation = fixtures.simulation_result()

    segment_ids = {segment.id for segment in graph.segments}
    persona_ids = {persona.id for persona in personas}

    for persona in personas:
        assert persona.segment_id in segment_ids

    for result in simulation.audience_results:
        assert result.persona_id in persona_ids

    for result in simulation.audience_segment_results:
        assert result.segment_id in segment_ids

    for edge in graph.adjacency:
        assert edge.from_segment_id in segment_ids
        assert edge.to_segment_id in segment_ids
