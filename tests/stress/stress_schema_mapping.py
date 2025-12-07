"""
Stress test to measure performance of schema mapping on a large synthetic database.
"""
import time
import unittest
from unittest.mock import MagicMock
from graphbot.services import InsightAgent, GeminiService

class TestStressSchema(unittest.TestCase):
    
    def setUp(self):
        # Mock Gemini Service
        self.mock_genai = MagicMock()
        self.service = GeminiService()
        self.service.worker_model = MagicMock()
        # Make the worker model response fast (mocked) to isolate schema extraction time
        self.service.worker_model.generate_content.return_value.text = "Stress test summary."
        
        self.agent = InsightAgent(self.service)
        
        # Create a Mock Neo4j session that returns a LARGE number of labels/rels
        self.mock_neo4j = MagicMock()
        self.mock_session = MagicMock()
        self.mock_neo4j.driver.session.return_value.__enter__.return_value = self.mock_session

    def test_large_schema_performance(self):
        """Simulate mapping a DB with 100 labels and 50 relationship types."""
        
        NUM_LABELS = 100
        NUM_RELS = 50
        
        # Generate synthetic data
        labels_result = [{"label": f"Entity_{i}"} for i in range(NUM_LABELS)]
        rels_result = [{"relationshipType": f"REL_{i}"} for i in range(NUM_RELS)]
        
        # Setup side effects for session.run
        # The sequence of calls in _extract_raw_schema is:
        # 1. db.labels()
        # 2. For each label: count(), props()
        # 3. db.relationshipTypes()
        # 4. For each rel: count()
        
        def side_effect(query, *args, **kwargs):
            if "CALL db.labels" in query:
                return labels_result
            elif "CALL db.relationshipTypes" in query:
                return rels_result
            elif "MATCH (n:`Entity_" in query:
                if "RETURN count" in query:
                    return [{"c": 1000}] # 1k nodes per label
                elif "RETURN keys" in query:
                    return [{"k": ["id", "name", "created_at", "status", "type"]}]
            elif "MATCH ()-[r:`REL_" in query:
                return [{"c": 5000}] # 5k rels per type
            return []

        self.mock_session.run.side_effect = side_effect
        
        print(f"\n🚀 Starting stress test: Mapping {NUM_LABELS} labels & {NUM_RELS} rel types...")
        start_time = time.time()
        
        result = self.agent.analyze_database(self.mock_neo4j)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Completed in {duration:.4f} seconds")
        
        # Assertions
        self.assertIn("raw_schema", result)
        # Check if output contains last label
        self.assertIn(f"Entity_{NUM_LABELS-1}", result["raw_schema"])
        
        # Performance Budget: Should be under 2 seconds for pure extraction logic (mocked DB)
        # If this fails, the loop logic in InsightAgent is too slow (CPU bound)
        self.assertLess(duration, 2.0, "Schema extraction logic is too slow!")

if __name__ == '__main__':
    unittest.main()

