"""`POST /ai/simulation/run`"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from fixtures import mock_metadata
from schemas import Envelope, SimulationRequest, SimulationResult, wrap

from .engine.engine import run_simulation

router = APIRouter(prefix="/ai/simulation", tags=["simulation"])


@router.post("/run", response_model=Envelope[SimulationResult])
async def post_run(request: SimulationRequest) -> Envelope[SimulationResult]:
    try:
        result, mock = await run_simulation(request)
    except RuntimeError as exc:
        # No personas at all — the run is genuinely impossible, unlike a few
        # failed personas, which come back as status='partial'.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return wrap(
        result,
        mock=mock,
        metadata=result.metadata or (mock_metadata() if mock else None),
    )
