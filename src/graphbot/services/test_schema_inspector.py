import pytest
from unittest.mock import MagicMock, AsyncMock
from graphbot.services.schema_inspector import SchemaInspector

@pytest.fixture
def inspector(mock_neo4j_driver):
    handler = MagicMock()
    handler.execute_query_async = AsyncMock()
    return SchemaInspector(handler)

@pytest.mark.asyncio
async def test_inspect_value_distribution(inspector):
    # Setup mock return
    inspector.neo4j.execute_query_async.return_value = [
        {"val": "A"}, {"val": "B"}
    ]
    
    values = await inspector.inspect_value_distribution("Person", "name", limit=5)
    
    assert len(values) == 2
    assert "A" in values
    assert "B" in values
    
    inspector.neo4j.execute_query_async.assert_called_once()
    args, kwargs = inspector.neo4j.execute_query_async.call_args
    assert "MATCH (n:`Person`)" in args[0]
    # Check the second argument for parameters
    assert args[1]["limit"] == 5

@pytest.mark.asyncio
async def test_inspect_value_distribution_error(inspector):
    inspector.neo4j.execute_query_async.side_effect = Exception("DB Error")
    
    values = await inspector.inspect_value_distribution("Person", "name")
    
    assert values == []

