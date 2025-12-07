import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from graphbot.services.unified_llm_service import UnifiedLLMService

@pytest.fixture
def mock_llm_factory():
    with patch("graphbot.services.unified_llm_service.LLMFactory") as factory:
        provider = MagicMock()
        provider.config = {
            "models": {"main": "gemini-pro", "worker": "gemini-flash"},
            "max_context_tokens": 1000,
            "provider": "google",
             "default_prompts": {}
        }
        provider.main_model = "gemini-pro"
        provider.generate_text = AsyncMock()
        # count_tokens must be awaitable
        provider.count_tokens = AsyncMock(return_value=10)
        factory.get_provider.return_value = provider
        yield factory

@pytest.fixture
def service(mock_llm_factory):
    # Mock open to avoid reading actual config file
    with patch("builtins.open", new_callable=MagicMock):
        return UnifiedLLMService("dummy_config.yaml")

@pytest.mark.asyncio
async def test_generate_cypher_query_async(service):
    provider = service._provider
    response = MagicMock()
    response.content = "MATCH (n) RETURN n"
    response.model_name = "gemini-pro"
    response.token_usage = 10
    provider.generate_text.return_value = response
    
    query = await service.generate_cypher_query_async("Show me nodes")
    
    assert query == "MATCH (n) RETURN n"
    provider.generate_text.assert_called_once()

@pytest.mark.asyncio
async def test_generate_cypher_query_strips_markdown(service):
    provider = service._provider
    response = MagicMock()
    response.content = "```cypher\nMATCH (n) RETURN n\n```"
    response.model_name = "gemini-pro"
    provider.generate_text.return_value = response
    
    query = await service.generate_cypher_query_async("Show me nodes")
    
    assert query == "MATCH (n) RETURN n"

@pytest.mark.asyncio
async def test_explain_result_async(service):
    provider = service._provider
    response = MagicMock()
    response.content = "This query returns all nodes."
    provider.generate_text.return_value = response

    explanation = await service.explain_result_async("MATCH (n) RETURN n", [{"n": "data"}], "Show me nodes")

    assert explanation == "This query returns all nodes."

@pytest.mark.asyncio
async def test_generate_cypher_query_with_context_truncation(service):
    """Test query generation with very long context that should be truncated."""
    provider = service._provider
    response = MagicMock()
    response.content = "MATCH (n) RETURN n"
    provider.generate_text.return_value = response

    # Create very long context
    long_context = "Schema info\n" * 1000  # Very long context
    query = await service.generate_cypher_query_async("Show me nodes", context=long_context)

    assert query == "MATCH (n) RETURN n"
    # Verify generate_text was called
    provider.generate_text.assert_called_once()

@pytest.mark.asyncio
async def test_generate_cypher_query_provider_failure(service):
    """Test handling of provider failures during query generation."""
    provider = service._provider
    provider.generate_text.side_effect = Exception("API Error")

    with pytest.raises(Exception, match="API Error"):
        await service.generate_cypher_query_async("Show me nodes")

@pytest.mark.asyncio
async def test_explain_result_empty_results(service):
    """Test explanation generation with empty results."""
    provider = service._provider
    response = MagicMock()
    response.content = "No results found."
    provider.generate_text.return_value = response

    explanation = await service.explain_result_async("MATCH (n) WHERE false RETURN n", [], "Show me nodes")

    assert explanation == "No results found."

@pytest.mark.asyncio
async def test_explain_result_provider_failure(service):
    """Test explanation generation when provider fails."""
    provider = service._provider
    provider.generate_text.side_effect = Exception("API Error")

    explanation = await service.explain_result_async("MATCH (n) RETURN n", [{"n": "data"}], "Show me nodes")

    assert explanation == "Could not generate explanation."

@pytest.mark.asyncio
async def test_get_worker_model_returns_adapter(service):
    """Test that get_worker_model returns the correct adapter."""
    worker_model = service.get_worker_model()

    # Should be a WorkerModelAdapter instance
    from graphbot.services.unified_llm_service import WorkerModelAdapter
    assert isinstance(worker_model, WorkerModelAdapter)

    # Test the adapter functionality
    provider = service._provider
    response = MagicMock()
    response.content = "Worker response"
    provider.generate_text.return_value = response

    result = await worker_model.generate_content_async("Test prompt")

    assert result.text == "Worker response"
    assert result.content == "Worker response"  # Check both attributes

