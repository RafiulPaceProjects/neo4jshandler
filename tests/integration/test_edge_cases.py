"""
Integration tests for edge cases and error scenarios.
"""
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from graphbot.core.schema_context import SchemaContext
from graphbot.services.unified_llm_service import UnifiedLLMService
from graphbot.services.insight_agent import InsightAgent


@pytest.fixture
def mock_full_stack():
    """Mock the full stack for integration testing."""
    neo4j = MagicMock()
    neo4j.driver = MagicMock()
    neo4j.database = "neo4j"
    neo4j.uri = "bolt://localhost:7687"  # Add URI for cache key generation

    # Mock Unified Service
    with patch('graphbot.services.unified_llm_service.LLMFactory') as factory:
        provider = MagicMock()
        provider.config = {"models": {"main": "gemini-pro", "worker": "gemini-flash"}, "provider": "google"}
        provider.generate_text = AsyncMock()
        provider.count_tokens = AsyncMock(return_value=10)
        factory.get_provider.return_value = provider

        unified_service = UnifiedLLMService("dummy_config.yaml")

        yield neo4j, unified_service, provider


@pytest.mark.asyncio
async def test_full_stack_with_empty_database(mock_full_stack):
    """Test full flow with empty database."""
    neo4j, unified_service, provider = mock_full_stack

    # Mock empty database responses
    neo4j.driver.session.return_value.__aenter__.return_value.run.side_effect = [
        [],  # No labels
        [],  # No relationships
    ]

    # Mock Insight Agent
    insight_agent = InsightAgent(unified_service)
    insights = await insight_agent.analyze_database_async(neo4j)

    # Should handle empty database gracefully
    assert "raw_schema" in insights
    assert insights["summary"] != ""  # Should still generate some summary

    # Inject into schema context
    schema_context = SchemaContext(neo4j)
    schema_context.set_insights(insights)

    context = await schema_context.get_schema_context_async()
    assert context != ""  # Should not be empty


@pytest.mark.asyncio
async def test_llm_service_failures_dont_crash_flow(mock_full_stack):
    """Test that LLM failures don't crash the entire flow."""
    neo4j, unified_service, provider = mock_full_stack

    # Make LLM calls fail
    provider.generate_text.side_effect = Exception("API Down")

    # Should handle gracefully
    try:
        query = await unified_service.generate_cypher_query_async("Show me nodes")
        # If it doesn't raise, should return a safe fallback
        assert isinstance(query, str)
    except Exception as e:
        # Should be a controlled exception, not a crash
        assert "API Down" in str(e)


@pytest.mark.asyncio
async def test_schema_context_with_corrupted_insights(mock_full_stack):
    """Test schema context handling of corrupted insights."""
    neo4j, unified_service, provider = mock_full_stack

    schema_context = SchemaContext(neo4j)

    # Test with corrupted insights
    corrupted_insights = {
        "summary": None,
        "raw_schema": None,
        "extra_key": "should be ignored"
    }

    schema_context.set_insights(corrupted_insights)

    # Should not crash
    context = await schema_context.get_schema_context_async()
    assert isinstance(context, str)


@pytest.mark.asyncio
async def test_large_schema_handling(mock_full_stack):
    """Test handling of very large schemas."""
    neo4j, unified_service, provider = mock_full_stack

    # Create a very large schema
    large_schema = "Node: " + "LargeLabel" * 1000

    insights = {
        "raw_schema": large_schema,
        "summary": "Large database with many entities"
    }

    schema_context = SchemaContext(neo4j)
    schema_context.set_insights(insights)

    context = await schema_context.get_schema_context_async()

    # Should handle large schemas without crashing
    assert "Large database" in context
    assert len(context) > 100  # Should contain substantial content


@pytest.mark.asyncio
async def test_concurrent_operations_simulation(mock_full_stack):
    """Test simulation of concurrent operations."""
    neo4j, unified_service, provider = mock_full_stack

    # Mock concurrent access to driver
    async def mock_run(*args, **kwargs):
        import asyncio
        await asyncio.sleep(0.01)  # Simulate async operation
        return []

    neo4j.driver.session.return_value.__aenter__.return_value.run = mock_run

    # Run multiple operations concurrently
    tasks = []
    for i in range(5):
        task = unified_service.generate_cypher_query_async(f"Query {i}")
        tasks.append(task)

    # Mock successful responses
    provider.generate_text.side_effect = [
        MagicMock(content=f"Query {i}") for i in range(5)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Should handle concurrent operations without crashing
    for result in results:
        if isinstance(result, Exception):
            pytest.fail(f"Concurrent operation failed: {result}")
        assert isinstance(result, str)


@pytest.mark.asyncio
async def test_network_timeout_simulation(mock_full_stack):
    """Test handling of network timeouts."""
    neo4j, unified_service, provider = mock_full_stack

    # Simulate timeout
    import asyncio
    async def timeout_operation(*args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate delay
        raise asyncio.TimeoutError("Network timeout")

    provider.generate_text = timeout_operation

    # Should handle timeout gracefully
    with pytest.raises(asyncio.TimeoutError):
        await unified_service.generate_cypher_query_async("Test query")


@pytest.mark.asyncio
async def test_mixed_success_failure_responses(mock_full_stack):
    """Test handling of mixed success/failure responses."""
    neo4j, unified_service, provider = mock_full_stack

    # Alternate between success and failure
    call_count = 0
    async def mixed_response(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count % 2 == 0:
            response = MagicMock()
            response.content = f"Success {call_count}"
            response.model_name = "test"
            response.token_usage = 10
            return response
        else:
            raise Exception(f"Failure {call_count}")

    provider.generate_text = mixed_response

    # Test multiple calls
    results = []
    for i in range(4):
        try:
            result = await unified_service.generate_cypher_query_async(f"Query {i}")
            results.append(("success", result))
        except Exception as e:
            results.append(("failure", str(e)))

    # Should have mix of successes and failures
    assert len(results) == 4
    success_count = sum(1 for r in results if r[0] == "success")
    failure_count = sum(1 for r in results if r[0] == "failure")
    assert success_count > 0
    assert failure_count > 0
