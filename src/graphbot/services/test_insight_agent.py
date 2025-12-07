import asyncio
import types
import pytest
from unittest.mock import MagicMock

from graphbot.services.insight_agent import InsightAgent


class AsyncIterator:
    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)


class DummyGemini:
    def __init__(self, worker_model):
        self._worker_model = worker_model

    def get_worker_model(self):
        return self._worker_model


class StubWorker:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    async def generate_content_async(self, prompt: str):
        self.prompts.append(prompt)
        text = self.responses.pop(0)
        return types.SimpleNamespace(text=text)


def test_generate_summary_uses_worker_model():
    worker = StubWorker(["This is a summary."])
    agent = InsightAgent(DummyGemini(worker))

    summary = asyncio.run(agent._generate_summary_async("Schema text here"))

    assert summary == "This is a summary."
    assert "Schema text here" in worker.prompts[0]


def test_suggest_questions_trims_and_limits():
    worker = StubWorker(
        [
            "Question one\n- Question two\n3. Question three\nQuestion four extra",
        ]
    )
    agent = InsightAgent(DummyGemini(worker))

    questions = asyncio.run(agent._suggest_questions_async("schema", "summary"))

    assert questions == ["Question one", "Question two", "Question three"]


def test_analyze_database_no_driver():
    """Test analyze_database when no driver is available."""
    mock_service = MagicMock()
    agent = InsightAgent(mock_service)
    mock_neo4j = MagicMock()
    mock_neo4j.driver = None

    result = agent.analyze_database(mock_neo4j)

    assert result["summary"] == "Could not analyze database (Not connected)."
    assert result["raw_schema"] == "Schema unavailable"


def test_generate_summary_error_handling():
    """Test summary generation error handling."""
    mock_service = MagicMock()
    agent = InsightAgent(mock_service)

    # Mock worker model to raise exception
    agent.worker_model.generate_content.side_effect = Exception("API Error")

    summary = agent._generate_summary("Some schema")

    assert summary.startswith("Summary generation failed")


def test_suggest_questions_error_handling():
    """Test question suggestion error handling."""
    mock_service = MagicMock()
    agent = InsightAgent(mock_service)

    # Mock worker model to raise exception
    agent.worker_model.generate_content.side_effect = Exception("API Error")

    questions = agent._suggest_questions("schema", "summary")

    assert questions == []


@pytest.mark.asyncio
async def test_extract_raw_schema_async_empty_database():
    """Test schema extraction from completely empty database."""
    mock_service = MagicMock()
    agent = InsightAgent(mock_service)
    mock_neo4j = MagicMock()

    # Mock session with empty results
    mock_session = MagicMock()
    mock_neo4j.driver.session.return_value.__aenter__.return_value = mock_session

    # Mock async run method
    async def mock_run(query):
        if "CALL db.labels" in query:
            return AsyncIterator([])
        elif "CALL db.relationshipTypes" in query:
            return AsyncIterator([])
        return AsyncIterator([])

    mock_session.run = mock_run

    schema = await agent._extract_raw_schema_async(mock_neo4j)

    assert "## Node Labels" in schema
    assert "## Relationships" in schema


@pytest.mark.asyncio
async def test_extract_raw_schema_async_partial_failures():
    """Test schema extraction when some queries fail but others succeed."""
    mock_service = MagicMock()
    agent = InsightAgent(mock_service)
    mock_neo4j = MagicMock()

    mock_session = MagicMock()
    mock_neo4j.driver.session.return_value.__aenter__.return_value = mock_session

    # Mock async run method with partial failures
    async def mock_run(query):
        if "CALL db.labels" in query:
            return AsyncIterator([{"label": "Person"}])
        elif "count(n)" in query and "Person" in query:
            raise Exception("Count failed")
        elif "keys(n)" in query and "Person" in query:
            return AsyncIterator([{"k": ["name"]}])
        elif "CALL db.relationshipTypes" in query:
            return AsyncIterator([{"relationshipType": "KNOWS"}])
        elif "count(r)" in query and "KNOWS" in query:
            return AsyncIterator([{"c": 5}])
        return AsyncIterator([])

    mock_session.run = mock_run

    schema = await agent._extract_raw_schema_async(mock_neo4j)

    # Should contain successful extractions and handle failures gracefully
    assert "Person" in schema
    assert "Error fetching stats" in schema
    assert "KNOWS" in schema

