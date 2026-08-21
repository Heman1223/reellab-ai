"""`POST /ai/counterfactual/generate`"""

from __future__ import annotations

from fastapi import APIRouter

from fixtures import mock_metadata
from schemas import CounterfactualExperiment, Envelope, ExperimentRequest, wrap

from .experiments.experiment import run_experiment

router = APIRouter(prefix="/ai/counterfactual", tags=["counterfactual"])


@router.post("/generate", response_model=Envelope[CounterfactualExperiment])
async def post_generate(request: ExperimentRequest) -> Envelope[CounterfactualExperiment]:
    # TODO(Developer 4): pass the real baseline simulation and Content DNA from
    # Mongo instead of letting the experiment fall back to fixtures. The
    # signature of `run_experiment` already accepts both.
    experiment, mock = await run_experiment(request)

    return wrap(
        experiment,
        mock=mock,
        metadata=experiment.metadata or (mock_metadata() if mock else None),
    )
