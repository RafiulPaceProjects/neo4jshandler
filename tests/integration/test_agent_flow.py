import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from graphbot.core import SchemaContext
from graphbot.services import InsightAgent, GeminiService

class TestAgentIntegration(unittest.TestCase):
    """
    Integration test simulating the full flow:
    InsightAgent maps DB -> Updates SchemaContext -> GeminiService uses Context
    """
    
    def setUp(self):
        self.mock_neo4j = MagicMock()
        
        # Mock Gemini Service to avoid real API calls
        self.mock_genai = MagicMock()
        with patch('graphbot.services.gemini_service.genai', self.mock_genai):
            self.gemini_service = GeminiService()
            # Ensure main_model methods are async mocks
            self.gemini_service.main_model = MagicMock()
            self.gemini_service.main_model.generate_content_async = AsyncMock()
            
        self.insight_agent = InsightAgent(self.gemini_service)
        self.schema_context = SchemaContext(self.mock_neo4j)

    def test_full_insight_flow(self):
        # 1. Mock Insight Agent Analysis
        # We'll bypass the internal heavy lifting and mock the return of analyze_database
        # to verify the hand-off between components
        
        simulated_insights = {
            "raw_schema": "Nodes: Patient, Doctor",
            "summary": "Healthcare database.",
            "suggested_questions": ["Count patients?"]
        }
        
        with patch.object(self.insight_agent, 'analyze_database', return_value=simulated_insights):
            insights = self.insight_agent.analyze_database(self.mock_neo4j)
            
        # 2. Inject into Context
        self.schema_context.set_insights(insights)
        
        # Verify Context State
        context_str = self.schema_context.get_schema_context()
        # Updated assertion to match new SchemaContext output format
        self.assertIn("Database Semantic Summary: Healthcare database.", context_str)
        self.assertIn("Technical Schema:\n\nNodes: Patient, Doctor", context_str)
        
        # 3. Use Context in Gemini Service
        # Mock the generate_content to capture the prompt
        mock_response = MagicMock()
        mock_response.text = "MATCH (n) RETURN count(n)"
        self.gemini_service.main_model.generate_content_async.return_value = mock_response
        
        # We need to run the async method in a loop or verify the call arguments
        # Since this is an integration test using unittest, we might not have async support easily unless we use IsolatedAsyncioTestCase
        # But let's see if generate_cypher_query is sync wrapper or async.
        # It calls asyncio.run inside generate_cypher_query (sync wrapper).
        
        self.gemini_service.generate_cypher_query("How many patients?", context=context_str)
        
        # Verify the Prompt contains our injected insights
        args, _ = self.gemini_service.main_model.generate_content_async.call_args
        prompt_sent = args[0]
        
        self.assertIn("### DATABASE SCHEMA:", prompt_sent)
        self.assertIn("Database Semantic Summary: Healthcare database.", prompt_sent)
        self.assertIn("Nodes: Patient, Doctor", prompt_sent)

if __name__ == '__main__':
    unittest.main()

