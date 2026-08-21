"""`POST /ai/evaluation/run`"""

from __future__ import annotations

from fastapi import APIRouter

from schemas import Envelope, EvaluationMetrics, EvaluationRequest, wrap

from .harness.harness import run_evaluation

router = APIRouter(prefix="/ai/evaluation", tags=["evaluation"])


@router.post("/run", response_model=Envelope[EvaluationMetrics])
async def post_run(request: EvaluationRequest) -> Envelope[EvaluationMetrics]:
    metrics = run_evaluation(request.predictions, request.dataset_id)
    # Metrics are computed from real ground truth, so this is never `mock` —
    # even though the ground truth itself is placeholder data for now.
    return wrap(metrics, mock=False)
