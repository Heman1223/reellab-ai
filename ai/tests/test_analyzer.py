from config import settings
import dataclasses
import pytest  # type: ignore
from pathlib import Path
import tempfile
import asyncio

from video_analysis.multimodal.analyzer import analyze_video
from errors import TranscriptionFailedError, MalformedModelOutputError
from schemas import ContentDNA
import video_analysis.multimodal.analyzer as mod


class MockMedia:
    def __init__(self, temp_dir):
        self.audio_path = "dummy_audio.wav"
        self.duration_seconds = 10.0
        self.frame_paths = [Path(temp_dir) / "frame_0.jpg"]
        self.frame_paths[0].touch()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockTranscript:
    def __init__(self, text="hello world"):
        self.text = text


@pytest.fixture
def mock_pipeline(monkeypatch):
    monkeypatch.setattr(mod, "extract_media", lambda x: MockMedia(tempfile.gettempdir()))
    monkeypatch.setattr(mod, "transcribe", lambda x: MockTranscript())
    
    class MockLLMResult:
        def __init__(self, data):
            self.data = data
            
    async def mock_complete_json(*args, **kwargs):
        return MockLLMResult({
            "video_id": "v1",
            "duration_seconds": 10.0,
            "transcript": "hello world",
            "topic": "test",
            "hook": {"text": "h", "duration_seconds": 1.0, "type": "test", "strength": 0.5},
            "tone": "test",
            "emotion": "test",
            "scenes": [],
            "visual_features": {"cuts_per_second": 1.0, "has_on_screen_text": False, "face_presence": 0.5},
            "audio_features": {"has_speech": True, "has_music": False, "words_per_minute": 100, "energy": 0.5},
            "cta": {"present": False},
        })
        
    class MockLLM:
        complete_json = mock_complete_json
        
    monkeypatch.setattr(mod, "llm", MockLLM())


@pytest.mark.asyncio
async def test_analyzer_success(mock_pipeline, monkeypatch):
    # Ensure not mock mode so it actually calls _analyze_with_model
    mock_settings = dataclasses.replace(settings, persona_provider='openai', openai_api_key='test', video_provider='gemini', gemini_api_key='test')
    monkeypatch.setattr('config.settings', mock_settings)
    monkeypatch.setattr('llm.settings', mock_settings)
    
    dna, mock = await analyze_video("test.mp4", "vid1")
    assert mock is False
    assert dna.video_id == "vid1"
    assert dna.topic == "test"


@pytest.mark.asyncio
async def test_transcription_failure_continues(mock_pipeline, monkeypatch):
    mock_settings = dataclasses.replace(settings, persona_provider='openai', openai_api_key='test', video_provider='gemini', gemini_api_key='test')
    monkeypatch.setattr('config.settings', mock_settings)
    monkeypatch.setattr('llm.settings', mock_settings)
    
    def failing_transcribe(x):
        raise TranscriptionFailedError("Mock failure")
        
    monkeypatch.setattr(mod, "transcribe", failing_transcribe)
    
    dna, mock = await analyze_video("test.mp4", "vid1")
    assert mock is False
    # Verify deterministic fallback: duration should override model, has_speech should be False
    assert dna.duration_seconds == 10.0
    assert dna.audio_features.has_speech is False
    assert dna.transcript == ""


@pytest.mark.asyncio
async def test_malformed_output_raises(mock_pipeline, monkeypatch):
    mock_settings = dataclasses.replace(settings, persona_provider='openai', openai_api_key='test', video_provider='gemini', gemini_api_key='test')
    monkeypatch.setattr('config.settings', mock_settings)
    monkeypatch.setattr('llm.settings', mock_settings)
    
    class MockLLMResult:
        def __init__(self, data):
            self.data = data
            
    async def bad_complete_json(*args, **kwargs):
        return MockLLMResult({"invalid": "schema"})
        
    monkeypatch.setattr(mod.llm, "complete_json", bad_complete_json)
    
    with pytest.raises(MalformedModelOutputError):
        await analyze_video("test.mp4", "vid1")
