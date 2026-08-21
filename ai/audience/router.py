"""`POST /ai/audience/discover`"""

from __future__ import annotations

from fastapi import APIRouter

from fixtures import mock_metadata
from schemas import AudienceGraph, AudienceRequest, Envelope, wrap

from .discovery.discovery import discover_audience

router = APIRouter(prefix="/ai/audience", tags=["audience"])


@router.post("/discover", response_model=Envelope[AudienceGraph])
async def post_discover(request: AudienceRequest) -> Envelope[AudienceGraph]:
    graph, mock = await discover_audience(request)
    return wrap(
        graph,
        mock=mock,
        metadata=mock_metadata() if mock else None,
    )
