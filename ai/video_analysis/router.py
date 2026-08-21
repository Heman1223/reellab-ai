"""`POST /ai/video/analyze`"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from fixtures import mock_metadata
from schemas import ContentDNA, Envelope, VideoAnalysisRequest, wrap

from .multimodal.analyzer import analyze_video

router = APIRouter(prefix="/ai/video", tags=["video"])


@router.post("/analyze", response_model=Envelope[ContentDNA])
async def post_analyze(request: VideoAnalysisRequest) -> Envelope[ContentDNA]:
    if not request.video_path and not request.video_url:
        raise HTTPException(
            status_code=422,
            detail="Provide either `videoPath` or `videoUrl`.",
        )

    # A path, never the bytes: the backend and the AI service share a filesystem
    # in both the local and the docker-compose setup, and a 100 MB multipart hop
    # between them would buy nothing.
    dna, mock = await analyze_video(
        video_path=request.video_path or request.video_url,
        video_id=request.video_id,
    )

    return wrap(dna, mock=mock, metadata=mock_metadata() if mock else None)
