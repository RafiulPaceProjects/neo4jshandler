import unittest
from unittest.mock import MagicMock, patch
from graphbot.services import InsightAgent

class TestInsightAgent(unittest.TestCase):
    
    def setUp(self):
        self.mock_service = MagicMock()
        self.agent = InsightAgent(self.mock_service)
        self.mock_neo4j = MagicMock()

    def test_schema_extraction_logic(self):
        """Test raw schema extraction with mocked Neo4j responses."""
        mock_session = MagicMock()
        self.mock_neo4j.driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock sequence of calls: db.labels, count(L1), props(L1), db.rels, count(R1)
        # Label: Person
        # Rel: KNOWS
        mock_session.run.side_effect = [
            [{"label": "Person"}], # db.labels
            {"c": 10}, # count Person
            {"k": ["name", "age"]}, # props Person
            [{"relationshipType": "KNOWS"}], # db.rels
            {"c": 5} # count KNOWS
        ]
        
        schema = self.agent._extract_raw_schema(self.mock_neo4j)
        
        self.assertIn("## Node Labels", schema)
        self.assertIn("- **Person**: 10 nodes. Properties: name, age", schema)
        self.assertIn("## Relationships", schema)
        self.assertIn("- **KNOWS**: 5 connections", schema)

    def test_summary_generation_error_handling(self):
        """Test that summary generation handles model errors gracefully."""
        # Mock worker model to raise exception
        self.agent.worker_model.generate_content.side_effect = Exception("API Error")
        
        summary = self.agent._generate_summary("Some schema")
        
        # Should return error message, not crash
        self.assertTrue(summary.startswith("Summary generation failed"))

    def test_zero_node_handling(self):
        """Test handling of labels with 0 nodes (regression test)."""
        mock_session = MagicMock()
        self.mock_neo4j.driver.session.return_value.__enter__.return_value = mock_session
        
        mock_session.run.side_effect = [
            [{"label": "Ghost"}], 
            {"c": 0}, # count 0
            # No prop call should happen if count is 0
            [{"relationshipType": "SPOOKS"}], 
            {"c": 0}
        ]
        
        schema = self.agent._extract_raw_schema(self.mock_neo4j)
        self.assertIn("- **Ghost**: 0 nodes.", schema)

if __name__ == '__main__':
    unittest.main()

