import unittest
from unittest.mock import MagicMock, patch
from graphbot.core import SchemaContext

class TestSchemaContext(unittest.TestCase):
    
    def setUp(self):
        self.mock_handler = MagicMock()
        self.schema_context = SchemaContext(self.mock_handler)

    def test_set_insights_injection(self):
        """Test that semantic insights are correctly injected into the schema context."""
        insights = {
            "summary": "A test database about movies.",
            "raw_schema": "- **Movie**: 100 nodes."
        }
        self.schema_context.set_insights(insights)
        
        context_str = self.schema_context.get_schema_context()
        
        self.assertIn("Domain Summary: A test database about movies.", context_str)
        self.assertIn("Technical Schema:\n- **Movie**: 100 nodes.", context_str)

    def test_fallback_schema_generation(self):
        """Test that legacy generation is called when no insights are provided."""
        # Setup mock for legacy generation
        mock_session = MagicMock()
        self.mock_handler.driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock node labels result
        mock_session.run.side_effect = [
            [{"labels": ["Person"]}, {"labels": ["Movie"]}], # db.labels
            [{"type": "ACTED_IN"}], # db.relationshipTypes
            [{"n": {"name": "Tom"}}], # Person sample
            {"count": 50}, # Person count
            [{"n": {"title": "Matrix"}}], # Movie sample
            {"count": 10}, # Movie count
            {"count": 20}, # Rel count
            [{"from_label": "Person", "to_label": "Movie"}] # Rel pattern
        ]
        
        schema = self.schema_context.get_schema_context()
        
        self.assertIn("Node Labels (entities):", schema)
        self.assertIn("- Movie", schema)
        self.assertIn("- Person", schema)
        self.assertIn("Relationship Types:", schema)

    def test_empty_database_resilience(self):
        """Test that the context handles an empty database without crashing."""
        mock_session = MagicMock()
        self.mock_handler.driver.session.return_value.__enter__.return_value = mock_session
        
        # Empty results
        mock_session.run.side_effect = [
            [], # No labels
            [], # No rels
        ]
        
        schema = self.schema_context.get_schema_context()
        self.assertIn("Node Labels (entities):", schema)
        self.assertIn("Relationship Types:", schema)

if __name__ == '__main__':
    unittest.main()

