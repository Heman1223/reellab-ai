"""ReelLab AI service.

    uvicorn main:app --reload --port 8000

A thin FastAPI shell over six modules. The HTTP layer does nothing but validate
input and wrap output — all the intelligence lives in the module packages, so it
can be tested and iterated on without a server running.

Endpoints:

    GET  /health
    POST /ai/audience/discover
    POST /ai/personas/generate
    POST /ai/video/analyze
    POST /ai/simulation/run
    POST /ai/counterfactual/generate
    POST /ai/evaluation/run
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from audience.router import router as audience_router
from config import REPO_ROOT, settings
from counterfactual.router import router as counterfactual_router
from errors import ReelLabAIError
from evaluation.router import router as evaluation_router
from logging_utils import configure_logging, get_logger, log_event
from personas.router import router as personas_router
from simulation.router import router as simulation_router
from video_analysis.preprocessing.preprocessing import ffmpeg_available
from video_analysis.router import router as video_router

configure_logging(settings.log_level)
logger = get_logger("main")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    log_event(
        logger,
        "ai_service_started",
        provider=settings.provider,
        mock_mode=settings.is_mock_mode,
        max_personas=settings.max_personas,
        ffmpeg=ffmpeg_available(),
    )
    yield
    log_event(logger, "ai_service_stopped")


app = FastAPI(
    title="ReelLab AI Service",
    description="Synthetic audience simulation and counterfactual experimentation.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """One structured line per request, with the backend's correlation id."""
    started = time.perf_counter()
    response = await call_next(request)
    log_event(
        logger,
        "http_request",
        request_id=request.headers.get("x-request-id"),
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    return response


@app.exception_handler(ReelLabAIError)
async def handle_reellab_error(request: Request, exc: ReelLabAIError) -> JSONResponse:
    """Map our error types onto the same envelope the Node backend uses."""
    log_event(
        logger,
        "request_failed",
        path=request.url.path,
        code=exc.code,
        error_message=exc.message,
    )
    return JSONResponse(status_code=exc.http_status, content={"error": exc.to_payload()})


@app.get("/health", tags=["health"])
async def health() -> dict:
    """Liveness plus an honest account of what this service can currently do."""
    return {
        "status": "ok",
        "service": "reellab-ai",
        "version": "0.1.0",
        "provider": settings.provider,
        "models": {
            "multimodal": settings.multimodal_model,
            "reasoning": settings.reasoning_model,
        },
        # True when no model will be called and fixtures are served instead.
        "mockMode": settings.is_mock_mode,
        "capabilities": {
            "ffmpeg": ffmpeg_available(),
            "modelCalls": not settings.is_mock_mode,
        },
        "repoRoot": str(REPO_ROOT),
    }


app.include_router(audience_router)
app.include_router(personas_router)
app.include_router(video_router)
app.include_router(simulation_router)
app.include_router(counterfactual_router)
app.include_router(evaluation_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level,
    )
