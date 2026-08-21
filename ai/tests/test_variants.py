import pytest
import asyncio
from counterfactual.generation.variants import generate_variants
from errors import MalformedModelOutputError
from schemas import ContentDNA, SimulationResult, Variant
import counterfactual.generation.variants as mod

class MockLLMResult:
    def __init__(self, data):
        self.data = data

@pytest.fixture
def mock_pipeline(monkeypatch):
    async def mock_complete_json(*args, **kwargs):
        # Default behavior: return 3 valid variants
        return MockLLMResult([
            {"label": "1", "description": "1", "new_asset": "1", "predicted_content_dna": {}},
            {"label": "2", "description": "2", "new_asset": "2", "predicted_content_dna": {}},
            {"label": "3", "description": "3", "new_asset": "3", "predicted_content_dna": {}}
        ])
        
    class MockLLM:
        complete_json = mock_complete_json
        
    monkeypatch.setattr(mod, "llm", MockLLM())


@pytest.fixture
def dummy_inputs():
    from tests.test_modules import fixtures
    return fixtures.content_dna(), fixtures.simulation_result()


@pytest.mark.asyncio
async def test_variant_generation_count(mock_pipeline, monkeypatch, dummy_inputs):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    content, sim = dummy_inputs
    variants, mock = await generate_variants(content, sim, modification_type="hook", count=2)
    
    assert mock is False
    # Model returns 3, but count enforces 2
    assert len(variants) == 2
    assert isinstance(variants[0], Variant)
    assert variants[0].id.startswith("var_")


@pytest.mark.asyncio
async def test_variant_malformed_output(monkeypatch, dummy_inputs):
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    async def bad_complete_json(*args, **kwargs):
        return MockLLMResult([{"label": "missing_fields"}])
        
    class MockLLM:
        complete_json = bad_complete_json
        
    monkeypatch.setattr(mod, "llm", MockLLM())
    
    content, sim = dummy_inputs
    with pytest.raises(MalformedModelOutputError):
        await generate_variants(content, sim, count=2)


@pytest.mark.asyncio
async def test_variant_nested_variants_key(monkeypatch, dummy_inputs):
    # Test handling of {"variants": [...]} output shape
    monkeypatch.setattr("config.settings.provider", "anthropic")
    monkeypatch.setattr("config.settings.api_key", "test")
    
    async def wrapped_complete_json(*args, **kwargs):
        return MockLLMResult({
            "variants": [
                {"label": "1", "description": "1", "new_asset": "1", "predicted_content_dna": {}}
            ]
        })
        
    class MockLLM:
        complete_json = wrapped_complete_json
        
    monkeypatch.setattr(mod, "llm", MockLLM())
    
    content, sim = dummy_inputs
    variants, mock = await generate_variants(content, sim, count=1)
    
    assert mock is False
    assert len(variants) == 1
