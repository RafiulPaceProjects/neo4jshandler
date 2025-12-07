import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_neo4j_driver():
    """Fixture for a mock Neo4j driver."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value = session
    return driver


@pytest.fixture
def mock_llm_provider():
    """Fixture for a mock LLM provider."""
    provider = MagicMock()
    provider.config = {
        "models": {"main": "gemini-pro", "worker": "gemini-flash"},
        "provider": "google",
        "default_prompts": {}
    }
    provider.main_model = "gemini-pro"
    provider.generate_text = AsyncMock()
    provider.count_tokens = AsyncMock(return_value=10)
    return provider

