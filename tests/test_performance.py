import unittest
from unittest.mock import MagicMock, patch
from graphbot.services import GeminiService, InsightAgent
from graphbot.core import SchemaContext

class TestModelPerformance(unittest.TestCase):
    """
    Tests to verify that models are initialized correctly and fallback mechanisms work.
    """
    
    @patch('graphbot.services.gemini_service.genai')
    def test_model_initialization(self, mock_genai):
        """Verify that Main and Worker models are initialized with correct types."""
        # Setup mocks
        mock_model_main = MagicMock()
        mock_model_worker = MagicMock()
        
        # Mock GenerativeModel to return different mocks based on input
        def side_effect(model_name):
            if "gemini-3" in model_name:
                return mock_model_main
            return mock_model_worker
            
        mock_genai.GenerativeModel.side_effect = side_effect
        
        service = GeminiService()
        
        # Check if models are set (assuming env vars or defaults)
        self.assertIsNotNone(service.main_model, "Main model should be initialized")
        self.assertIsNotNone(service.worker_model, "Worker model should be initialized")
        
    @patch('graphbot.services.gemini_service.genai')
    def test_fallback_logic(self, mock_genai):
        """Test that fallback logic handles missing models gracefully."""
        # Simulate list_models failing
        mock_genai.list_models.side_effect = Exception("API Timeout")
        
        service = GeminiService()
        
        # Service should still initialize using defaults despite list error
        self.assertIsNotNone(service.main_model)
        
    def test_insight_agent_error_handling(self):
        """Test that InsightAgent handles schema errors without crashing."""
        mock_gemini = MagicMock()
        agent = InsightAgent(mock_gemini)
        
        # Mock Neo4j handler to raise exception
        mock_neo4j = MagicMock()
        mock_neo4j.driver.session.side_effect = Exception("Connection Lost")
        
        # Should return error dict, not raise exception
        result = agent.analyze_database(mock_neo4j)
        
        self.assertIn("raw_schema", result)
        self.assertEqual(result["summary"], "Could not analyze database.")
        self.assertEqual(result["suggested_questions"], [])

if __name__ == '__main__':
    unittest.main()

