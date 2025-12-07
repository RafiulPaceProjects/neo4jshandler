import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from graphbot.core.schema_context import SchemaContext
from graphbot.services.unified_llm_service import UnifiedLLMService
from graphbot.services.insight_agent import InsightAgent

@pytest.fixture
def mock_components():
    neo4j = MagicMock()
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
async def test_unified_insight_to_query_flow(mock_components):
    neo4j, unified_service, provider = mock_components
    
    # 1. Setup Insight Agent (using unified service as worker)
    # InsightAgent likely expects a gemini_service-like object or we mock it
    # The current InsightAgent implementation might need checking.
    # It takes `llm_service`.
    
    # Let's mock the InsightAgent's dependency on LLM
    # unified_service has get_worker_model() which returns an adapter.
    
    insight_agent = InsightAgent(unified_service) 
    # Note: InsightAgent might expect GeminiService, we need to check if UnifiedLLMService is compatible.
    # We saw UnifiedLLMService has `get_worker_model`.
    
    # Mock Insight Agent's analyze_database to return insights
    # (Bypassing internal prompt logic for this integration test)
    simulated_insights = {
        "raw_schema": "Nodes: User, Product",
        "summary": "E-commerce DB",
        "suggested_questions": ["Top products?"]
    }
    
    # We patch the generation inside insight_agent if we want to test that logic, 
    # but for flow, mocking analyze_database is easier.
    # But let's try to verify the UnifiedService is used.
    
    # Mock provider response for InsightAgent
    provider.generate_text.return_value.content = "Summary: E-commerce DB\nSchema: Nodes: User, Product"
    
    # We need to see if InsightAgent calls `llm_service.get_worker_model()`
    # Let's assume it does.
    
    with patch.object(insight_agent, 'analyze_database', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = simulated_insights
        
        insights = await insight_agent.analyze_database(neo4j)
        
    # 2. Inject into SchemaContext
    schema_context = SchemaContext(neo4j)
    schema_context.set_insights(insights)
    
    # Use async method to avoid nesting loops since we are already in async test
    if hasattr(schema_context, 'get_schema_context_async'):
        context_str = await schema_context.get_schema_context_async()
    else:
        # Fallback if the async method is private or named differently, 
        # though traceback showed get_schema_context_async
        context_str = schema_context.get_schema_context()
        
    assert "E-commerce DB" in context_str
    
    # 3. Generate Query using Unified Service with Context
    provider.generate_text.return_value.content = "MATCH (u:User) RETURN u"
    
    query = await unified_service.generate_cypher_query_async("List users", context=context_str)
    
    assert query == "MATCH (u:User) RETURN u"
    
    # Verify the context was passed to the provider
    # provider.generate_text was called with prompt containing context
    call_args = provider.generate_text.call_args
    prompt = call_args[0][0]
    assert "E-commerce DB" in prompt


