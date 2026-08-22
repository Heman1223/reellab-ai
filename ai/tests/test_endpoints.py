"""HTTP surface tests for the AI service.

Asserts the shape of the contract the Node backend depends on: every endpoint
answers, every payload is wrapped in `{data, mock, metadata}`, and every key on
the wire is camelCase.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from config import MOCK_DIR
from main import app

client = TestClient(app)


def _example(name: str) -> dict:
    """Load a canonical request payload from `shared/examples/`."""
    path = Path(MOCK_DIR).parent.parent / "shared" / "examples" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_health_reports_mock_mode():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "reellab-ai"
    assert body["mockMode"] is True
    assert body["capabilities"]["modelCalls"] is False


def test_audience_discover_accepts_the_canonical_example():
    response = client.post("/ai/audience/discover", json=_example("audience-request.example.json"))

    assert response.status_code == 200
    body = response.json()
    assert body["mock"] is True
    assert len(body["data"]["segments"]) >= 3
    # camelCase on the wire, always.
    assert "relevanceScore" in body["data"]["segments"][0]
    assert "parentSegment" in body["data"]["segments"][0]


def test_audience_discover_rejects_an_incomplete_request():
    response = client.post("/ai/audience/discover", json={"niche": "fitness"})
    assert response.status_code == 422


def test_personas_generate():
    graph = client.post(
        "/ai/audience/discover", json=_example("audience-request.example.json")
    ).json()["data"]
    segment = next(s for s in graph["segments"] if s["parentSegment"] is not None)

    response = client.post(
        "/ai/personas/generate", json={"segment": segment, "count": 2}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mock"] is True
    assert body["data"]
    assert "attentionProfile" in body["data"][0]
    assert "engagementProfile" in body["data"][0]


def test_video_analyze_returns_content_dna():
    response = client.post(
        "/ai/video/analyze",
        json={"videoPath": "data/sample_reels/example.mp4", "videoId": "reel_test"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["videoId"] == "reel_test"
    assert "hook" in body["data"]
    assert "visualFeatures" in body["data"]


def test_video_analyze_requires_a_source():
    response = client.post("/ai/video/analyze", json={})
    assert response.status_code == 422


def test_simulation_run_returns_a_complete_result():
    response = client.post("/ai/simulation/run", json={"reelId": "reel_001"})

    assert response.status_code == 200
    body = response.json()
    data = body["data"]

    assert data["simulationId"].startswith("sim_")
    assert data["status"] in {"completed", "partial"}
    for key in (
        "overallScore",
        "confidence",
        "audienceResults",
        "propagationWaves",
        "audienceSegmentResults",
        "bottlenecks",
        "warnings",
    ):
        assert key in data, f"SimulationResult is missing '{key}'"

    assert data["audienceResults"][0]["reason"]
    assert body["metadata"]["mock"] is True


def test_counterfactual_generate_produces_variants_and_a_recommendation():
    response = client.post(
        "/ai/counterfactual/generate",
        json=_example("experiment-request.example.json"),
    )

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["experimentId"].startswith("exp_")
    assert data["variants"]
    assert data["recommendation"]["reasoning"]
    assert "modificationType" in data


def test_evaluation_run_scores_predictions():
    response = client.post(
        "/ai/evaluation/run",
        json={
            "predictions": [
                {
                    "reelId": "eval_reel_002",
                    "predictedScore": 0.9,
                    "predictedRank": 1,
                    "confidence": 0.7,
                },
                {
                    "reelId": "eval_reel_003",
                    "predictedScore": 0.6,
                    "predictedRank": 2,
                    "confidence": 0.7,
                },
                {
                    "reelId": "eval_reel_001",
                    "predictedScore": 0.3,
                    "predictedRank": 3,
                    "confidence": 0.7,
                },
            ]
        },
    )

    assert response.status_code == 200
    metrics = response.json()["data"]
    assert metrics["itemCount"] == 3
    assert metrics["pairwiseRankingAccuracy"] == 1.0
