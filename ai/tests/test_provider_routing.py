import pytest  # type: ignore
import asyncio
from pathlib import Path

from config import settings
from llm import llm, LLMClient, GeminiProvider, HuggingFaceProvider
from errors import AINotConfiguredError

@pytest.fixture(autouse=True)
def reset_llm_stats():
    llm.stats.failures = 0
    llm.stats.calls = 0

def test_1_reasoning_provider(monkeypatch):
    """TEST 1 - Verify tier='reasoning' selects GeminiProvider."""
    monkeypatch.setattr(settings, "provider", "gemini")
    monkeypatch.setattr(settings, "api_key", "test_gemini_key")
    
    provider = llm.provider_for("reasoning")
    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"

def test_2_multimodal_provider(monkeypatch):
    """TEST 2 - Verify tier='multimodal' selects HuggingFaceProvider."""
    monkeypatch.setattr(settings, "multimodal_provider", "huggingface")
    monkeypatch.setattr(settings, "hf_token", "test_hf_token")
    
    provider = llm.provider_for("multimodal")
    assert isinstance(provider, HuggingFaceProvider)
    assert provider.name == "huggingface"

def test_3_model_separation(monkeypatch):
    """TEST 3 - Verify reasoning -> REASONING_MODEL and multimodal -> HF_MODEL."""
    monkeypatch.setattr(settings, "reasoning_model", "test-gemini-model")
    monkeypatch.setattr(settings, "multimodal_model", "test-gemma-model")
    
    assert llm.model_for("reasoning") == "test-gemini-model"
    assert llm.model_for("multimodal") == "test-gemma-model"

@pytest.mark.asyncio
async def test_4_gemini_regression(monkeypatch):
    """TEST 4 - Verify Gemini reasoning calls remain compatible."""
    monkeypatch.setattr(settings, "provider", "gemini")
    monkeypatch.setattr(settings, "api_key", "test_gemini_key")
    monkeypatch.setattr(settings, "reasoning_model", "test-gemini-model")
    
    # Mock the GeminiProvider so it doesn't make real network calls
    class MockProvider(GeminiProvider):
        async def generate_structured(self, **kwargs):
            from llm import ProviderResponse
            return ProviderResponse(data={"success": True}, model=self.name)
            
    monkeypatch.setitem(llm.__module__ + ".PROVIDERS", "gemini", lambda key: MockProvider(key))
    
    # Needs a dummy schema for complete_json
    result = await llm.complete_json(
        prompt="test",
        prompt_version="v1",
        tier="reasoning",
        schema={"type": "object", "properties": {"success": {"type": "boolean"}}}
    )
    assert result.data == {"success": True}

@pytest.mark.asyncio
async def test_5_missing_hf_token(monkeypatch):
    """TEST 5 - Verify missing HF token affects only multimodal, not reasoning."""
    monkeypatch.setattr(settings, "provider", "gemini")
    monkeypatch.setattr(settings, "api_key", "test_gemini_key")
    monkeypatch.setattr(settings, "multimodal_provider", "huggingface")
    monkeypatch.setattr(settings, "hf_token", "")  # Missing token
    
    # Reasoning should still be fine
    assert llm.is_configured("reasoning") is True
    provider = llm.provider_for("reasoning")
    assert isinstance(provider, GeminiProvider)
    
    # Multimodal should fail
    assert llm.is_configured("multimodal") is False
    with pytest.raises(AINotConfiguredError, match="HF_TOKEN is empty"):
        llm.provider_for("multimodal")

@pytest.mark.asyncio
async def test_6_existing_multimodal_call(monkeypatch):
    """TEST 6 - Verify complete_json(tier='multimodal') reaches HuggingFaceProvider."""
    monkeypatch.setattr(settings, "multimodal_provider", "huggingface")
    monkeypatch.setattr(settings, "hf_token", "test_hf_token")
    monkeypatch.setattr(settings, "multimodal_model", "google/gemma-4-31B-it")
    
    called_model = None
    class MockHFProvider(HuggingFaceProvider):
        async def generate_structured(self, **kwargs):
            nonlocal called_model
            called_model = kwargs.get("model")
            from llm import ProviderResponse
            return ProviderResponse(data={"scene": "test"}, model=called_model)
            
    monkeypatch.setitem(llm.__module__ + ".PROVIDERS", "huggingface", lambda key: MockHFProvider(key))
    
    result = await llm.complete_json(
        prompt="analyze",
        prompt_version="v1",
        tier="multimodal",
        schema={"type": "object", "properties": {"scene": {"type": "string"}}}
    )
    assert result.data == {"scene": "test"}
    assert called_model == "google/gemma-4-31B-it"

@pytest.mark.asyncio
async def test_7_fallback_behavior(monkeypatch):
    """TEST 7 - Verify fallback behavior when provider is unavailable."""
    monkeypatch.setattr(settings, "provider", "mock")
    monkeypatch.setattr(settings, "api_key", "")
    
    from llm import with_fixture_fallback
    
    async def failing_call():
        raise AINotConfiguredError("Test failure")
        
    def mock_fixture():
        return "fallback"
        
    result, is_mock = await with_fixture_fallback("test_op", failing_call, mock_fixture)
    assert result == "fallback"
    assert is_mock is True
