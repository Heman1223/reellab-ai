"""Frame and audio extraction.

Deterministic media handling only. FFmpeg does the work; no model calls belong
in this file. Keeping extraction separate from interpretation means Developer 2
can verify "did we get usable frames?" independently of "did the model
understand them?" — two failures that look identical from the outside.

Nothing here is implemented yet. FFmpeg is a system binary, not a pip package:
check `ffmpeg -version` works before starting.

OWNER: Developer 2.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from errors import UnsupportedVideoError

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}


@dataclass
class ExtractedMedia:
    """Everything pulled off a video file before any model sees it."""

    video_path: Path
    duration_seconds: float
    frame_paths: list[Path]
    audio_path: Path | None
    width: int
    height: int


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def validate_video(video_path: str | Path) -> Path:
    """Check the file exists and is a format we accept. Raises on failure."""
    path = Path(video_path)

    if not path.is_file():
        raise UnsupportedVideoError(f"No file at '{path}'.", details={"path": str(path)})

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise UnsupportedVideoError(
            f"'{path.suffix}' is not a supported video format.",
            details={"supported": sorted(SUPPORTED_EXTENSIONS)},
        )

    if path.stat().st_size == 0:
        raise UnsupportedVideoError("File is empty.", details={"path": str(path)})

    return path


def extract_media(video_path: str | Path, frames_per_second: float = 1.0) -> ExtractedMedia:
    """Pull frames and the audio track out of a reel.

    TODO(Developer 2):
      - `ffprobe` for duration and dimensions.
      - `ffmpeg -i <in> -vf fps=<n> <out>/frame_%04d.jpg` for frames. One frame
        per second is plenty for a 30-second reel; the hook window deserves
        denser sampling than the rest.
      - `ffmpeg -i <in> -vn -ac 1 -ar 16000 <out>/audio.wav` for audio.
      - Write to a temp directory and clean it up; frames are large and the
        `uploads/` folder is already gitignored for a reason.
      - Raise `UnsupportedVideoError` on a non-zero FFmpeg exit.
    """
    path = validate_video(video_path)

    if not ffmpeg_available():
        raise UnsupportedVideoError(
            "FFmpeg is not on PATH. Install it before running video analysis.",
        )

    raise NotImplementedError(
        f"extract_media is not implemented yet (ai/video_analysis/preprocessing/). "
        f"Would process: {path}"
    )
