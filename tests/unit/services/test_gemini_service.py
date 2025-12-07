import unittest
from unittest.mock import MagicMock, patch
from graphbot.services import GeminiService

class TestGeminiService(unittest.TestCase):
    
    @patch('graphbot.services.gemini_service.genai')
    def test_dual_model_initialization(self, mock_genai):
        """Test that both Main and Worker models are initialized."""
        # Mock list_models to return empty list to trigger fallback or defaults
        mock_genai.list_models.return_value = []
        
        service = GeminiService()
        
        self.assertIsNotNone(service.main_model)
        self.assertIsNotNone(service.worker_model)
        
        # Default names
        self.assertEqual(service.main_model_name, 'gemini-3-pro-preview')
        self.assertEqual(service.worker_model_name, 'gemini-1.5-flash')

    @patch('graphbot.services.gemini_service.genai')
    def test_prompt_construction(self, mock_genai):
        """Test that context is correctly added to the prompt."""
        service = GeminiService()
        service.main_model = MagicMock()
        
        # Setup a predictable response
        mock_response = MagicMock()
        mock_response.text = "MATCH (n) RETURN n"
        service.main_model.generate_content.return_value = mock_response
        
        context = "Schema: (Person)-[:KNOWS]->(Person)"
        query = service.generate_cypher_query("Find friends", context=context)
        
        # meaningful prompt check
        args, _ = service.main_model.generate_content.call_args
        prompt_sent = args[0]
        self.assertIn(context, prompt_sent)
        self.assertIn("User request: Find friends", prompt_sent)

    def test_extract_text_resilience(self):
        """Test text extraction from different response structures."""
        service = GeminiService()
        # Bypassing init for helper test
        
        # Case 1: response.text attribute
        resp1 = MagicMock()
        resp1.text = "Query 1"
        self.assertEqual(service._extract_text(resp1), "Query 1")
        
        # Case 2: response.parts (list of objects with text)
        resp2 = MagicMock()
        part = MagicMock()
        part.text = "Query 2"
        del resp2.text # Ensure it falls back
        resp2.parts = [part]
        self.assertEqual(service._extract_text(resp2), "Query 2")

if __name__ == '__main__':
    unittest.main()

