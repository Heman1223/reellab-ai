"""Frame and audio extraction.

Deterministic media handling only. FFmpeg does the work; no model calls belong
in this file. Keeping extraction separate from interpretation means Developer 2
can verify "did we get usable frames?" independently of "did the model
understand them?" — two failures that look identical from the outside.

OWNER: Developer 2.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import urllib.request
import urllib.parse

from errors import UnsupportedVideoError

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}


@dataclass
class ExtractedMedia:
    """Everything pulled off a video file before any model sees it.
    
    This is a context manager. You MUST use it in a `with` block or manually
    call `cleanup()` to avoid leaking temporary directories full of frames.
    """

    video_path: Path
    duration_seconds: float
    frame_paths: list[Path]
    audio_path: Path | None
    width: int
    height: int
    _temp_dir: tempfile.TemporaryDirectory | None = field(repr=False, default=None)

    def __enter__(self) -> ExtractedMedia:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def validate_video(video_path: str | Path) -> Path:
    """Check the file exists and is a format we accept. Raises on failure."""
    path = Path(video_path)

    if not path.exists():
        raise UnsupportedVideoError(f"No file at '{path}'.", details={"path": str(path)})

    if not path.is_file():
        raise UnsupportedVideoError(f"'{path}' is not a file.", details={"path": str(path)})

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise UnsupportedVideoError(
            f"'{path.suffix}' is not a supported video format.",
            details={"supported": sorted(SUPPORTED_EXTENSIONS)},
        )

    if path.stat().st_size == 0:
        raise UnsupportedVideoError("File is empty.", details={"path": str(path)})

    return path


def get_sampling_timestamps(duration: float, max_frames: int = 10) -> list[float]:
    """Calculate exact timestamps to extract frames from."""
    if duration <= 0.1:
        return [0.0]
        
    if duration <= 5.0:
        count = min(max(1, int(duration)), max_frames)
        interval = duration / count
        return [round((i * interval) + (interval / 2), 2) for i in range(count)]
        
    timestamps = [0.5, 1.5, 2.5]
    remaining_duration = duration - 3.0
    body_max_frames = max_frames - len(timestamps)
    body_frames = min(body_max_frames, max(1, int(remaining_duration)))
    
    if body_frames > 0:
        interval = remaining_duration / body_frames
        for i in range(body_frames):
            ts = 3.0 + (i * interval) + (interval / 2)
            if ts < duration:
                timestamps.append(ts)
                
    return sorted(list(set(round(t, 2) for t in timestamps if t < duration)))


def _run_subprocess(cmd: list[str], error_message: str) -> subprocess.CompletedProcess:
    """Run a subprocess securely with timeout and error handling."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise UnsupportedVideoError(
                error_message,
                details={"cmd": " ".join(cmd), "stderr": result.stderr.strip()}
            )
        return result
    except subprocess.TimeoutExpired as exc:
        raise UnsupportedVideoError(f"{error_message} (Timed out after 120s)") from exc
    except Exception as exc:
        if isinstance(exc, UnsupportedVideoError):
            raise
        raise UnsupportedVideoError(f"{error_message}: {str(exc)}") from exc


def extract_media(video_path: str | Path, max_frames: int = 5) -> ExtractedMedia:
    """Pull frames and the audio track out of a reel."""
    is_url = str(video_path).startswith("http://") or str(video_path).startswith("https://")
    
    temp_dir = tempfile.TemporaryDirectory(prefix="reellab_media_")
    temp_path = Path(temp_dir.name)
    
    if is_url:
        url = str(video_path)
        download_path = temp_path / "downloaded_video.mp4"
        try:
            urllib.request.urlretrieve(url, download_path)
            video_path = download_path
        except Exception as e:
            temp_dir.cleanup()
            raise UnsupportedVideoError(f"Failed to download video from URL: {e}")
            
    path = validate_video(video_path)

    if not ffmpeg_available():
        raise UnsupportedVideoError(
            "FFmpeg/FFprobe are not on PATH. Install them before running video analysis.",
        )

    cmd_probe = [
        "ffprobe", "-v", "error", 
        "-show_entries", "format=duration:stream=width,height,codec_type",
        "-of", "json", str(path)
    ]
    probe_res = _run_subprocess(cmd_probe, "Failed to extract video metadata")
    
    try:
        probe_data = json.loads(probe_res.stdout)
    except json.JSONDecodeError:
        raise UnsupportedVideoError("FFprobe returned invalid JSON output.")
        
    format_info = probe_data.get("format", {})
    streams_info = probe_data.get("streams", [])
    
    try:
        duration = float(format_info.get("duration", 0.0))
    except (ValueError, TypeError):
        raise UnsupportedVideoError("Could not parse video duration.")
        
    if duration <= 0:
        raise UnsupportedVideoError("Video duration is zero or missing.")
        
    video_streams = [s for s in streams_info if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams_info if s.get("codec_type") == "audio"]
    
    if not video_streams:
        raise UnsupportedVideoError("No video stream found in the file.")
        
    width = int(video_streams[0].get("width", 0))
    height = int(video_streams[0].get("height", 0))
    has_audio = len(audio_streams) > 0
    
    try:
        timestamps = get_sampling_timestamps(duration, max_frames)
        frame_paths = []
        
        for i, ts in enumerate(timestamps):
            out_frame = temp_path / f"frame_{i:04d}.jpg"
            cmd_frame = [
                "ffmpeg", "-y", "-v", "error",
                "-ss", str(ts),
                "-i", str(path),
                "-vframes", "1",
                "-q:v", "2",
                str(out_frame)
            ]
            _run_subprocess(cmd_frame, f"Failed to extract frame at {ts}s")
            
            if out_frame.exists() and out_frame.stat().st_size > 0:
                frame_paths.append(out_frame)
                
        if not frame_paths:
            raise UnsupportedVideoError("Failed to extract any usable frames.")

        audio_path = None
        if has_audio:
            out_audio = temp_path / "audio.wav"
            cmd_audio = [
                "ffmpeg", "-y", "-v", "error",
                "-i", str(path),
                "-vn", "-ac", "1", "-ar", "16000",
                str(out_audio)
            ]
            _run_subprocess(cmd_audio, "Failed to extract audio track")
            
            if out_audio.exists() and out_audio.stat().st_size > 0:
                audio_path = out_audio
                
        return ExtractedMedia(
            video_path=path,
            duration_seconds=duration,
            frame_paths=frame_paths,
            audio_path=audio_path,
            width=width,
            height=height,
            _temp_dir=temp_dir
        )
    except Exception:
        temp_dir.cleanup()
        raise
