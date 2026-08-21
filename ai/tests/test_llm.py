import pytest
import base64
from pathlib import Path
import tempfile
import asyncio

from llm import LLMClient
from errors import AINotConfiguredError, MalformedModelOutputError, ReelLabAIError

class MockMessage:
    def __init__(self, content):
        self.content = content
        self.usage = type("Usage", (), {"input_tokens": 10, "output_tokens": 20})()

class MockBlock:
    def __init__(self, type, name, input_data):
        self.type = type
        self.name = name
        self.input = input_data

class MockClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.messages = self

    async def create(self, model, max_tokens, messages, tools, tool_choice):
        self.last_messages = messages
        self.last_tools = tools
        self.last_tool_choice = tool_choice
        
        # Determine if we should fail based on prompt
        prompt = messages[0]["content"][-1]["text"]
        if "FAIL_API" in prompt:
            raise RuntimeError("API failure")
        if "NO_TOOL_CALL" in prompt:
            return MockMessage([MockBlock("text", "text", {})])
        if "MISSING_RESPONSE" in prompt:
            return MockMessage([MockBlock("tool_use", "return_json", {})])
        if "NON_DICT_RESPONSE" in prompt:
            return MockMessage([MockBlock("tool_use", "return_json", {"response": "a string"})])
            
        return MockMessage([MockBlock("tool_use", "return_json", {"response": {"success": True}})])


@pytest.fixture
def mock_anthropic(monkeypatch):
    class MockAnthropicModule:
        AsyncAnthropic = MockClient
    
    monkeypatch.setattr("llm.anthropic", MockAnthropicModule)


@pytest.mark.asyncio
async def test_unconfigured(monkeypatch):
    monkeypatch.setattr("config.settings.provider", "mock")
    monkeypatch.setattr("config.settings.api_key", "")
    
    client = LLMClient()
    with pytest.raises(AINotConfiguredError):
        await client.complete_json(prompt="test", prompt_version="v1")


@pytest.mark.asyncio
async def test_text_only_reasoning(mock_anthropic, monkeypatch):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test_key")
    
    client = LLMClient()
    result = await client.complete_json(
        prompt="test prompt",
        prompt_version="v1",
        tier="reasoning"
    )
    
    assert result.data == {"success": True}
    assert result.metadata.input_tokens == 10
    assert result.metadata.output_tokens == 20


@pytest.mark.asyncio
async def test_multimodal_frames(mock_anthropic, monkeypatch):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test_key")
    
    client = LLMClient()
    
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        # Create some dummy frames
        f1 = p / "frame_0001.jpg"
        f1.write_bytes(b"image1")
        f2 = p / "frame_0002.jpg"
        f2.write_bytes(b"image2")
        
        # Test
        result = await client.complete_json(
            prompt="analyze this",
            prompt_version="v1",
            tier="multimodal",
            media_path=td
        )
        assert result.data == {"success": True}

@pytest.mark.asyncio
async def test_malformed_output(mock_anthropic, monkeypatch):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test_key")
    
    client = LLMClient()
    
    with pytest.raises(MalformedModelOutputError):
        await client.complete_json(prompt="NO_TOOL_CALL", prompt_version="v1")
        
    with pytest.raises(MalformedModelOutputError):
        await client.complete_json(prompt="MISSING_RESPONSE", prompt_version="v1")
        
    with pytest.raises(MalformedModelOutputError):
        await client.complete_json(prompt="NON_DICT_RESPONSE", prompt_version="v1")
        
    with pytest.raises(ReelLabAIError, match="Anthropic API call failed"):
        await client.complete_json(prompt="FAIL_API", prompt_version="v1")
