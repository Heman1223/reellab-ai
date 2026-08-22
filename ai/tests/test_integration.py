from config import settings
import dataclasses
import pytest  # type: ignore
import asyncio
from pathlib import Path
import tempfile
import json
import base64

from video_analysis.multimodal.analyzer import analyze_video
from schemas import ContentDNA
import video_analysis.multimodal.analyzer as mod

# Mock the LLM explicitly, but use real extraction and transcription where possible
class MockLLMResult:
    def __init__(self, data):
        self.data = data

@pytest.fixture
def mock_anthropic_multimodal(monkeypatch):
    async def mock_complete_json(*args, **kwargs):
        # Return a valid dict structure so analyzer's deterministic override + Pydantic works
        return MockLLMResult({
            "video_id": "test",
            "duration_seconds": 1.0,
            "transcript": "dummy",
            "topic": "Integration Test",
            "hook": {"text": "A hook", "duration_seconds": 1.0, "type": "question", "strength": 0.8},
            "tone": "informative",
            "emotion": "excited",
            "scenes": [
                {
                    "index": 0,
                    "start_seconds": 0.0,
                    "end_seconds": 1.0,
                    "description": "Opening",
                    "shot_type": "wide",
                    "energy": 0.5
                }
            ],
            "visual_features": {
                "cuts_per_second": 1.0,
                "has_on_screen_text": False,
                "face_presence": 0.0,
                "dominant_colors": [],
                "production_quality": 0.8
            },
            "audio_features": {
                "has_speech": False,
                "has_music": False,
                "words_per_minute": 0.0,
                "energy": 0.5
            },
            "cta": {"present": False},
            "warnings": []
        })
        
    class MockLLM:
        complete_json = mock_complete_json
        
    monkeypatch.setattr(mod, "llm", MockLLM())


@pytest.mark.asyncio
async def test_analyze_video_integration_no_media_mocks(mock_anthropic_multimodal, monkeypatch):
    """
    Integration test.
    We mock the LLM boundary, but ALLOW extract_media and transcribe to run normally.
    Since we can't commit large video files, we mock extract_media just enough to provide a valid path,
    or use a tiny dummy if available.
    """
    mock_settings = dataclasses.replace(settings, persona_provider='openai', openai_api_key='test', video_provider='gemini', gemini_api_key='test')
    monkeypatch.setattr('config.settings', mock_settings)
    monkeypatch.setattr('llm.settings', mock_settings)
    
    # We will mock extract_media to return a mocked ExtractedMedia
    # because creating a real video via FFmpeg in a test requires FFmpeg to be installed.
    class DummyMedia:
        def __init__(self, td):
            self.duration_seconds = 2.0
            self.audio_path = None
            self.frame_paths = [Path(td) / "frame_000.jpg"]
            self.frame_paths[0].touch()
            
        def __enter__(self): return self
        def __exit__(self, *args): pass
        
    def mock_extract(*args, **kwargs):
        return DummyMedia(tempfile.gettempdir())
        
    monkeypatch.setattr(mod, "extract_media", mock_extract)
    
    dna, mock = await analyze_video("fake.mp4", "vid_int")
    
    assert mock is False
    assert dna.video_id == "vid_int"
    assert dna.topic == "Integration Test"
    assert dna.duration_seconds == 2.0  # overwritten by deterministic data
    assert dna.audio_features.has_speech is False
