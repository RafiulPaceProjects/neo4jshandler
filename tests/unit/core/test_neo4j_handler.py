import unittest
from unittest.mock import MagicMock, patch
from graphbot.handlers import Neo4jHandler

class TestNeo4jHandler(unittest.TestCase):
    
    @patch('graphbot.handlers.neo4j_handler.GraphDatabase')
    def test_connection_fallback(self, mock_gdb):
        """Test that the handler tries fallback URIs including Docker host."""
        mock_driver = MagicMock()
        mock_gdb.driver.return_value = mock_driver
        
        # Simulate failure on first attempts, success on last
        mock_driver.verify_connectivity.side_effect = [Exception("Fail 1"), Exception("Fail 2"), Exception("Fail 3"), Exception("Fail 4"), None]
        
        # Initialize handler (which calls _connect)
        # We need to mock env vars or pass them, but __init__ uses env
        with patch.dict('os.environ', {'NEO4J_URI': 'bolt://bad-host:7687', 'NEO4J_PASSWORD': 'pass'}):
            handler = Neo4jHandler()
            
        # Check if it eventually connected
        self.assertTrue(handler.test_connection())
        self.assertEqual(mock_gdb.driver.call_count, 5) # Configured + 3 fallbacks + Docker fallback

    def test_format_results(self):
        """Test result formatting logic."""
        # Bypass connection for this test
        with patch('graphbot.handlers.neo4j_handler.Neo4jHandler._connect'):
            handler = Neo4jHandler()
            handler.driver = MagicMock()
            
        # Test Node formatting
        node_result = [{
            'n': {
                'type': 'Node',
                'labels': ['Person'],
                'properties': {'name': 'Alice', 'age': 30}
            }
        }]
        formatted = handler.format_results(node_result)
        self.assertIn("(Person {name: Alice, age: 30})", formatted)
        
        # Test Rel formatting
        rel_result = [{
            'r': {
                'type': 'Relationship',
                'type_name': 'KNOWS',
                'properties': {'since': 2020}
            }
        }]
        formatted_rel = handler.format_results(rel_result)
        self.assertIn("-[KNOWS {since: 2020}]->", formatted_rel)

if __name__ == '__main__':
    unittest.main()

