import pytest  # type: ignore
import asyncio
import dataclasses
from pathlib import Path

from config import settings
from llm import llm, LLMClient, GeminiProvider, OpenAIProvider
from errors import AINotConfiguredError

@pytest.fixture(autouse=True)
def reset_llm_stats():
    llm.stats.failures = 0
    llm.stats.calls = 0

def mock_settings(monkeypatch, **kwargs):
    new_settings = dataclasses.replace(settings, **kwargs)
    monkeypatch.setattr("llm.settings", new_settings)
    # Some other modules might import settings directly from config
    monkeypatch.setattr("config.settings", new_settings)
    return new_settings

def test_1_reasoning_provider(monkeypatch):
    """TEST 1 - Verify tier='reasoning' selects OpenAIProvider."""
    mock_settings(
        monkeypatch, 
        persona_provider="openai", 
        openai_api_key="test_openai_key"
    )
    
    provider = llm.provider_for("reasoning")
    assert isinstance(provider, OpenAIProvider)
    assert provider.name == "openai"
    assert provider._api_key == "test_openai_key"

def test_2_multimodal_provider(monkeypatch):
    """TEST 2 - Verify tier='multimodal' selects GeminiProvider."""
    mock_settings(
        monkeypatch, 
        video_provider="gemini", 
        gemini_api_key="test_gemini_key"
    )
    
    provider = llm.provider_for("multimodal")
    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"
    assert provider._api_key == "test_gemini_key"

def test_3_model_separation(monkeypatch):
    """TEST 3 - Verify reasoning -> PERSONA_MODEL and multimodal -> VIDEO_MODEL."""
    mock_settings(
        monkeypatch,
        persona_model="test-openai-model",
        video_model="test-gemini-model"
    )
    
    assert llm.model_for("reasoning") == "test-openai-model"
    assert llm.model_for("multimodal") == "test-gemini-model"

@pytest.mark.asyncio
async def test_4_openai_reasoning(monkeypatch):
    """TEST 4 - Verify OpenAI reasoning calls work correctly."""
    mock_settings(
        monkeypatch,
        persona_provider="openai",
        openai_api_key="test_openai_key",
        persona_model="gpt-4o"
    )
    
    class MockProvider(OpenAIProvider):
        def __init__(self, api_key):
            super().__init__(api_key)
            
        async def generate_structured(self, **kwargs):
            from llm import ProviderResponse
            return ProviderResponse(data={"success": True}, model=self.name)
            
    import llm as llm_module
    monkeypatch.setitem(llm_module.PROVIDERS, "openai", lambda key: MockProvider(key))
    
    result = await llm.complete_json(
        prompt="test",
        prompt_version="v1",
        tier="reasoning",
        schema={"type": "object", "properties": {"success": {"type": "boolean"}}}
    )
    assert result.data == {"success": True}

@pytest.mark.asyncio
async def test_5_missing_keys(monkeypatch):
    """TEST 5 - Verify missing keys isolate failures to their tier."""
    # Missing OpenAI key, but Gemini key exists
    mock_settings(
        monkeypatch,
        persona_provider="openai",
        openai_api_key="",
        video_provider="gemini",
        gemini_api_key="test_gemini_key"
    )
    
    # Multimodal should still be fine
    assert llm.is_configured("multimodal") is True
    provider = llm.provider_for("multimodal")
    assert isinstance(provider, GeminiProvider)
    
    # Reasoning should fail
    assert llm.is_configured("reasoning") is False
    with pytest.raises(AINotConfiguredError, match="OPENAI_API_KEY is empty"):
        llm.provider_for("reasoning")

@pytest.mark.asyncio
async def test_6_multimodal_call(monkeypatch):
    """TEST 6 - Verify complete_json(tier='multimodal') reaches GeminiProvider."""
    mock_settings(
        monkeypatch,
        video_provider="gemini",
        gemini_api_key="test_gemini_key",
        video_model="gemini-3.1-pro"
    )
    
    called_model = None
    class MockGeminiProvider(GeminiProvider):
        def __init__(self, api_key):
            super().__init__(api_key)
            
        async def generate_structured(self, **kwargs):
            nonlocal called_model
            called_model = kwargs.get("model")
            from llm import ProviderResponse
            return ProviderResponse(data={"scene": "test"}, model=called_model)
            
    import llm as llm_module
    monkeypatch.setitem(llm_module.PROVIDERS, "gemini", lambda key: MockGeminiProvider(key))
    
    result = await llm.complete_json(
        prompt="analyze",
        prompt_version="v1",
        tier="multimodal",
        schema={"type": "object", "properties": {"scene": {"type": "string"}}}
    )
    assert result.data == {"scene": "test"}
    assert called_model == "gemini-3.1-pro"

@pytest.mark.asyncio
async def test_7_fallback_behavior(monkeypatch):
    """TEST 7 - Verify fallback behavior when provider is unavailable."""
    mock_settings(
        monkeypatch,
        persona_provider="mock",
        openai_api_key=""
    )
    
    from llm import with_fixture_fallback
    
    async def failing_call():
        raise AINotConfiguredError("Test failure")
        
    def mock_fixture():
        return "fallback"
        
    result, is_mock = await with_fixture_fallback("test_op", failing_call, mock_fixture)
    assert result == "fallback"
    assert is_mock is True
