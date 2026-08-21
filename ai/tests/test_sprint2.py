import pytest  # type: ignore
import asyncio
from pathlib import Path
import tempfile

from video_analysis.multimodal.analyzer import analyze_video
from counterfactual.generation.variants import generate_variants
from llm import LLMClient
from errors import (
    MalformedModelOutputError, 
    AINotConfiguredError, 
    ModelTimeoutError,
    TranscriptionFailedError
)
from schemas import ContentDNA, Variant, SimulationResult
from tests.test_modules import fixtures
import video_analysis.multimodal.analyzer as analyzer_mod
import counterfactual.generation.variants as variant_mod

class MockLLMResult:
    def __init__(self, data):
        self.data = data

@pytest.fixture
def mock_dummy_media(monkeypatch):
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
        
    monkeypatch.setattr(analyzer_mod, "extract_media", mock_extract)

@pytest.fixture
def dummy_sim():
    return fixtures.simulation_result()

@pytest.fixture
def dummy_content():
    return fixtures.content_dna()


# --- CONTENT DNA & HOOK & CTA TESTS ---

@pytest.mark.asyncio
async def test_analyzer_deterministic_overrides(mock_dummy_media, monkeypatch):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    async def mock_complete(*args, **kwargs):
        return MockLLMResult({
            "video_id": "hallucinated", 
            "duration_seconds": 999.0, # LLM hallucination
            "transcript": "Fake words", # LLM hallucination
            "topic": "test",
            "hook": {"text": "h", "duration_seconds": 1.0, "type": "question", "strength": 0.5},
            "tone": "test",
            "emotion": "test",
            "scenes": [
                {"index": 0, "start_seconds": 0.0, "end_seconds": 99.0, "description": "Too long", "shot_type": "wide", "energy": 0.5},
                {"index": 1, "start_seconds": 50.0, "end_seconds": 2.0, "description": "Out of order", "shot_type": "wide", "energy": 0.5}
            ],
            "visual_features": {"cuts_per_second": 1.0, "has_on_screen_text": False, "face_presence": 0.5},
            "audio_features": {"has_speech": True, "has_music": False, "words_per_minute": 900, "energy": 0.5},
            "cta": {"present": True, "text": "Like!", "type": "other"}
        })
        
    class MockLLM:
        complete_json = mock_complete
    monkeypatch.setattr(analyzer_mod, "llm", MockLLM())
    
    dna, mock = await analyze_video("fake.mp4", "vid1")
    assert mock is False
    # Deterministic overrides
    assert dna.duration_seconds == 2.0
    assert dna.transcript == ""
    assert dna.audio_features.has_speech is False
    
    # Scene bounds clamped and ordered
    assert dna.scenes[0].start_seconds == 0.0
    assert dna.scenes[0].end_seconds == 2.0
    assert dna.scenes[1].start_seconds == 2.0
    assert dna.scenes[1].end_seconds == 2.0

@pytest.mark.asyncio
async def test_analyzer_invalid_hook_type(mock_dummy_media, monkeypatch):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    async def mock_complete(*args, **kwargs):
        return MockLLMResult({
            # MISSING HOOK OR WRONG TYPE
            "hook": "this is a string not an object"
        })
    monkeypatch.setattr(analyzer_mod.llm, "complete_json", mock_complete)
    with pytest.raises(MalformedModelOutputError):
        await analyze_video("fake.mp4", "vid1")


# --- COUNTERFACTUALS TESTS ---

@pytest.mark.asyncio
async def test_counterfactual_modification_lever(monkeypatch, dummy_content, dummy_sim):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    prompt_captured = ""
    async def mock_complete(prompt, *args, **kwargs):
        nonlocal prompt_captured
        prompt_captured = prompt
        return MockLLMResult([])
        
    class MockLLM:
        complete_json = mock_complete
    monkeypatch.setattr(variant_mod, "llm", MockLLM())
    
    await generate_variants(dummy_content, dummy_sim, modification_type="pacing", count=1)
    
    # Verify the prompt explicitly passes the pacing instruction
    assert "pacing" in prompt_captured
    assert "focus strictly on pacing/cuts/timing" in prompt_captured


@pytest.mark.asyncio
async def test_counterfactual_count_enforcement(monkeypatch, dummy_content, dummy_sim):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    async def mock_complete(*args, **kwargs):
        return MockLLMResult([
            {"label": "1", "description": "1", "new_asset": "1", "predicted_content_dna": {}},
            {"label": "2", "description": "2", "new_asset": "2", "predicted_content_dna": {}},
            {"label": "3", "description": "3", "new_asset": "3", "predicted_content_dna": {}}
        ])
        
    class MockLLM:
        complete_json = mock_complete
    monkeypatch.setattr(variant_mod, "llm", MockLLM())
    
    vars, mock = await generate_variants(dummy_content, dummy_sim, modification_type="hook", count=1)
    assert len(vars) == 1


# --- LLM BOUNDARY TESTS ---

@pytest.mark.asyncio
async def test_llm_timeout_mapping(monkeypatch):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    class MockAnthropic:
        class APITimeoutError(Exception): pass
        
        class MockClient:
            def __init__(self, *args, **kwargs): pass
            @property
            def messages(self):
                class Msg:
                    async def create(self, *args, **kwargs):
                        raise MockAnthropic.APITimeoutError("timeout")
                return Msg()
                
        AsyncAnthropic = MockClient
        
    monkeypatch.setattr("llm.anthropic", MockAnthropic)
    client = LLMClient()
    
    with pytest.raises(ModelTimeoutError):
        await client.complete_json(prompt="test", prompt_version="v1")
