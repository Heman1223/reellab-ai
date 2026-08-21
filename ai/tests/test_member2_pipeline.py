import pytest
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
from video_analysis.preprocessing.preprocessing import ExtractedMedia


class MockLLMResult:
    def __init__(self, data):
        self.data = data

@pytest.fixture
def mock_dummy_media(monkeypatch):
    class DummyMedia:
        def __init__(self, td):
            self.duration_seconds = 5.0
            self.audio_path = Path(td) / "audio.wav"
            self.audio_path.touch()
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


# CASE 1: Valid video + AI unavailable
@pytest.mark.asyncio
async def test_case_1_ai_unavailable(mock_dummy_media, monkeypatch):
    monkeypatch.setattr("config.settings.provider", "")
    monkeypatch.setattr("config.settings.api_key", "")
    
    dna, mock = await analyze_video("fake.mp4", "vid1")
    assert mock is True
    assert isinstance(dna, ContentDNA)


# CASE 2: Valid video + no audio
@pytest.mark.asyncio
async def test_case_2_no_audio(mock_dummy_media, monkeypatch):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    class DummyMediaNoAudio:
        def __init__(self, td):
            self.duration_seconds = 5.0
            self.audio_path = None
            self.frame_paths = [Path(td) / "frame.jpg"]
            self.frame_paths[0].touch()
        def __enter__(self): return self
        def __exit__(self, *args): pass
        
    monkeypatch.setattr(analyzer_mod, "extract_media", lambda *a, **kw: DummyMediaNoAudio(tempfile.gettempdir()))
    
    async def mock_complete(*args, **kwargs):
        return MockLLMResult(fixtures.content_dna().model_dump())
    
    monkeypatch.setattr(analyzer_mod.llm, "complete_json", mock_complete)
    
    dna, mock = await analyze_video("fake.mp4", "vid1")
    assert mock is False
    assert dna.audio_features.has_speech is False
    assert dna.transcript == ""


# CASE 3: Valid video + transcription failure
@pytest.mark.asyncio
async def test_case_3_transcription_failure(mock_dummy_media, monkeypatch):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    def mock_transcribe(*args, **kwargs):
        raise TranscriptionFailedError("mock crash")
    monkeypatch.setattr(analyzer_mod, "transcribe", mock_transcribe)
    
    async def mock_complete(*args, **kwargs):
        return MockLLMResult(fixtures.content_dna().model_dump())
    
    monkeypatch.setattr(analyzer_mod.llm, "complete_json", mock_complete)
    
    dna, mock = await analyze_video("fake.mp4", "vid1")
    assert mock is False
    assert dna.audio_features.has_speech is False
    assert dna.transcript == ""


# CASE 4: Valid video + malformed LLM output
@pytest.mark.asyncio
async def test_case_4_malformed_llm(mock_dummy_media, monkeypatch):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    async def mock_complete(*args, **kwargs):
        return MockLLMResult({"missing": "everything"})
    monkeypatch.setattr(analyzer_mod.llm, "complete_json", mock_complete)
    
    with pytest.raises(MalformedModelOutputError):
        await analyze_video("fake.mp4", "vid1")


# CASE 5: Valid video + valid LLM output
@pytest.mark.asyncio
async def test_case_5_valid_llm(mock_dummy_media, monkeypatch):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    async def mock_complete(*args, **kwargs):
        return MockLLMResult(fixtures.content_dna().model_dump())
    monkeypatch.setattr(analyzer_mod.llm, "complete_json", mock_complete)
    
    dna, mock = await analyze_video("fake.mp4", "vid1")
    assert mock is False
    assert isinstance(dna, ContentDNA)


# CASE 6: Counterfactual generation
@pytest.mark.asyncio
async def test_case_6_counterfactuals(monkeypatch, dummy_content, dummy_sim):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    async def mock_complete(*args, **kwargs):
        # Unwrapped output
        return MockLLMResult([
            {"label": "1", "description": "d", "new_asset": "a", "predicted_content_dna": fixtures.content_dna().model_dump()},
            {"label": "2", "description": "d", "new_asset": "a", "predicted_content_dna": fixtures.content_dna().model_dump()}
        ])
    monkeypatch.setattr(variant_mod.llm, "complete_json", mock_complete)
    
    variants, mock = await generate_variants(dummy_content, dummy_sim, count=2)
    assert mock is False
    assert len(variants) == 2


# CASE 7: Counterfactual malformed output
@pytest.mark.asyncio
async def test_case_7_counterfactual_malformed(monkeypatch, dummy_content, dummy_sim):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    async def mock_complete(*args, **kwargs):
        return MockLLMResult([{"bad": "variant"}])
    monkeypatch.setattr(variant_mod.llm, "complete_json", mock_complete)
    
    with pytest.raises(MalformedModelOutputError):
        await generate_variants(dummy_content, dummy_sim, count=1)


# CASE 8: Reasoning LLM call backward compatibility
@pytest.mark.asyncio
async def test_case_8_reasoning_llm_call(monkeypatch):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    # We mock the anthropic client to just verify the payload
    passed_kwargs = {}
    class MockAnthropic:
        class Msg:
            async def create(self, **kwargs):
                nonlocal passed_kwargs
                passed_kwargs = kwargs
                
                class Block:
                    type = "tool_use"
                    name = "return_json"
                    input = {"response": {"ok": True}}
                    
                class Res:
                    content = [Block()]
                    class Usage:
                        input_tokens = 1
                        output_tokens = 1
                    usage = Usage()
                return Res()
        
        class MockClient:
            def __init__(self, *args, **kwargs): pass
            @property
            def messages(self): return MockAnthropic.Msg()
            
        AsyncAnthropic = MockClient
        
    monkeypatch.setattr("llm.anthropic", MockAnthropic)
    
    client = LLMClient()
    res = await client.complete_json(prompt="test", prompt_version="v", tier="reasoning")
    
    assert res.data == {"ok": True}
    assert passed_kwargs["model"] == "claude-3-5-haiku-20241022"
    assert len(passed_kwargs["messages"][0]["content"]) == 1
    assert passed_kwargs["messages"][0]["content"][0]["type"] == "text"


# CASE 9: Multimodal LLM call with frames
@pytest.mark.asyncio
async def test_case_9_multimodal_llm_call(monkeypatch):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    passed_kwargs = {}
    class MockAnthropic:
        class Msg:
            async def create(self, **kwargs):
                nonlocal passed_kwargs
                passed_kwargs = kwargs
                
                class Block:
                    type = "tool_use"
                    name = "return_json"
                    input = {"response": {"ok": True}}
                    
                class Res:
                    content = [Block()]
                    class Usage:
                        input_tokens = 1
                        output_tokens = 1
                    usage = Usage()
                return Res()
        
        class MockClient:
            def __init__(self, *args, **kwargs): pass
            @property
            def messages(self): return MockAnthropic.Msg()
            
        AsyncAnthropic = MockClient
        
    monkeypatch.setattr("llm.anthropic", MockAnthropic)
    
    client = LLMClient()
    
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p / "frame_0.jpg").write_bytes(b"image")
        (p / "frame_1.jpg").write_bytes(b"image")
        
        res = await client.complete_json(prompt="test", prompt_version="v", tier="multimodal", media_path=str(td))
        
        assert passed_kwargs["model"] == "claude-3-5-sonnet-20241022"
        # 2 images + 1 text
        assert len(passed_kwargs["messages"][0]["content"]) == 3
        assert passed_kwargs["messages"][0]["content"][0]["type"] == "image"
        assert passed_kwargs["messages"][0]["content"][1]["type"] == "image"
        assert passed_kwargs["messages"][0]["content"][2]["type"] == "text"


# CASE 10: Temporary media cleanup
def test_case_10_media_cleanup(monkeypatch):
    def mock_subprocess(*args, **kwargs):
        # Create fake output
        Path(kwargs.get("cwd", ".")).joinpath("frame_000.jpg").touch()
        class Res: returncode = 0
        return Res()
        
    monkeypatch.setattr("video_analysis.preprocessing.preprocessing.subprocess.run", mock_subprocess)
    monkeypatch.setattr("video_analysis.preprocessing.preprocessing.validate_video", lambda p: Path(p))
    
    import video_analysis.preprocessing.preprocessing as pp
    pp.ffmpeg_available = lambda: True
    
    td_path = None
    with ExtractedMedia(Path("fake.mp4"), 5.0, [], None, 100, 100) as media:
        media._temp_dir = tempfile.TemporaryDirectory()
        td_path = Path(media._temp_dir.name)
        assert td_path.exists()
        
    assert not td_path.exists()
