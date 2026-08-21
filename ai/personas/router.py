"""`POST /ai/personas/generate`"""

from __future__ import annotations

from fastapi import APIRouter

from fixtures import mock_metadata
from schemas import Envelope, Persona, PersonaGenerationRequest, wrap

from .generation.generator import generate_personas

router = APIRouter(prefix="/ai/personas", tags=["personas"])


@router.post("/generate", response_model=Envelope[list[Persona]])
async def post_generate(request: PersonaGenerationRequest) -> Envelope[list[Persona]]:
    personas, mock = await generate_personas(
        request.segment, request.count, request.creator_goal
    )
    return wrap(
        personas,
        mock=mock,
        metadata=mock_metadata(persona_count=len(personas)) if mock else None,
    )
