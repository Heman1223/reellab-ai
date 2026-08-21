import pytest
from pathlib import Path
import tempfile

from video_analysis.transcription.transcription import (
    transcribe,
    Transcript,
    TranscriptSegment
)
from errors import TranscriptionFailedError, AINotConfiguredError
import video_analysis.transcription.transcription as mod

class MockSegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text

class MockInfo:
    def __init__(self, language):
        self.language = language

class MockWhisperModel:
    def __init__(self, model_size, device="cpu", compute_type="int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.should_fail = False
        self.mock_segments = []
        
    def transcribe(self, audio_path, beam_size=5):
        if self.should_fail:
            raise RuntimeError("Mock failure")
        def generator():
            for seg in self.mock_segments:
                yield seg
        return generator(), MockInfo("en")


def test_transcribe_none_path():
    result = transcribe(None)
    assert result.is_empty
    assert result.segments == []


def test_transcribe_nonexistent_path():
    result = transcribe("does_not_exist.wav")
    assert result.is_empty
    assert result.segments == []


def test_transcribe_success(monkeypatch):
    mock_model = MockWhisperModel("base")
    mock_model.mock_segments = [
        MockSegment(0.0, 2.0, "Hello world."),
        MockSegment(2.5, 4.0, "This is a test.")
    ]
    monkeypatch.setattr(mod, "_get_model", lambda: mock_model)
    
    with tempfile.NamedTemporaryFile(suffix=".wav") as tf:
        result = transcribe(tf.name)
        
    assert not result.is_empty
    assert result.text == "Hello world. This is a test."
    assert result.language == "en"
    assert len(result.segments) == 2
    assert result.segments[0].start_seconds == 0.0
    assert result.segments[0].end_seconds == 2.0
    assert result.segments[0].text == "Hello world."
    assert result.segments[1].text == "This is a test."


def test_transcribe_silent_audio(monkeypatch):
    mock_model = MockWhisperModel("base")
    mock_model.mock_segments = []
    monkeypatch.setattr(mod, "_get_model", lambda: mock_model)
    
    with tempfile.NamedTemporaryFile(suffix=".wav") as tf:
        result = transcribe(tf.name)
        
    assert result.is_empty
    assert result.text == ""
    assert result.segments == []


def test_transcribe_failure(monkeypatch):
    mock_model = MockWhisperModel("base")
    mock_model.should_fail = True
    monkeypatch.setattr(mod, "_get_model", lambda: mock_model)
    
    with tempfile.NamedTemporaryFile(suffix=".wav") as tf:
        with pytest.raises(TranscriptionFailedError, match="Whisper inference failed: Mock failure"):
            transcribe(tf.name)


def test_missing_dependency(monkeypatch):
    monkeypatch.setattr(mod, "WhisperModel", None)
    monkeypatch.setattr(mod, "_model", None)
    
    with tempfile.NamedTemporaryFile(suffix=".wav") as tf:
        with pytest.raises(AINotConfiguredError, match="faster-whisper is not installed"):
            transcribe(tf.name)
