import pytest  # type: ignore
from pathlib import Path
import tempfile
import shutil

from video_analysis.preprocessing.preprocessing import (
    validate_video,
    get_sampling_timestamps,
    extract_media,
    ffmpeg_available
)
from errors import UnsupportedVideoError


def test_validate_video_nonexistent():
    with pytest.raises(UnsupportedVideoError, match="No file at"):
        validate_video("does_not_exist.mp4")


def test_validate_video_unsupported_ext():
    with tempfile.NamedTemporaryFile(suffix=".txt") as tf:
        with pytest.raises(UnsupportedVideoError, match="not a supported video format"):
            validate_video(tf.name)


def test_validate_video_empty():
    with tempfile.NamedTemporaryFile(suffix=".mp4") as tf:
        with pytest.raises(UnsupportedVideoError, match="File is empty"):
            validate_video(tf.name)


def test_get_sampling_timestamps_zero():
    assert get_sampling_timestamps(0.0) == [0.0]


def test_get_sampling_timestamps_short():
    ts = get_sampling_timestamps(3.0, 10)
    assert ts == [0.5, 1.5, 2.5]


def test_get_sampling_timestamps_medium():
    ts = get_sampling_timestamps(10.0, 10)
    assert 0.5 in ts
    assert 1.5 in ts
    assert 2.5 in ts
    assert len(ts) <= 10
    assert all(t < 10.0 for t in ts)
    assert len(set(ts)) == len(ts)


def test_get_sampling_timestamps_long():
    ts = get_sampling_timestamps(100.0, 10)
    assert 0.5 in ts
    assert 1.5 in ts
    assert 2.5 in ts
    assert len(ts) == 10
    assert all(t < 100.0 for t in ts)


@pytest.mark.skipif(not ffmpeg_available(), reason="FFmpeg not available")
def test_extract_media_corrupt_file():
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        tf.write(b"not a video file at all" * 1000)
        tf.flush()
        
    try:
        with pytest.raises(UnsupportedVideoError):
            with extract_media(tf.name):
                pass
    finally:
        Path(tf.name).unlink(missing_ok=True)
