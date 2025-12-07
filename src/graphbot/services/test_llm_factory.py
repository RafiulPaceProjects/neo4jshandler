import pytest
import os
import yaml
from unittest.mock import patch, MagicMock
from graphbot.services.llm import LLMFactory, GeminiProvider, LLMProvider, LLMResponse
from graphbot.services.context_manager import ContextManager

# Sample config for testing
TEST_CONFIG = {
    "version": "1.0",
    "active_profile": "test_gemini",
    "profiles": {
        "test_gemini": {
            "provider": "google",
            "api_key_env_var": "TEST_KEY",
            "models": {"main": "gemini-test", "worker": "gemini-worker"},
            "max_context_tokens": 100
        }
    }
}

@pytest.fixture
def mock_config_file(tmp_path):
    config_path = tmp_path / "providers.yaml"
    with open(config_path, "w") as f:
        yaml.dump(TEST_CONFIG, f)
    return str(config_path)

@patch("graphbot.services.llm.os.getenv")
@patch("google.generativeai.configure")
def test_factory_creates_gemini_provider(mock_configure, mock_getenv, mock_config_file):
    mock_getenv.return_value = "fake_key"
    
    provider = LLMFactory.get_provider(mock_config_file)
    
    assert isinstance(provider, GeminiProvider)
    assert provider.main_model == "gemini-test"
    mock_configure.assert_called_once_with(api_key="fake_key")

@pytest.mark.asyncio
async def test_context_manager_truncation():
    # Mock provider
    provider = MagicMock(spec=LLMProvider)
    # Simple mock: 1 char = 1 token for easy math
    async def mock_count(text):
        return len(text)
    provider.count_tokens = mock_count
    
    manager = ContextManager(provider, max_tokens=50) # Small limit
    
    user_input = "Hello world" # 11 tokens
    system = "You are a bot" # 13 tokens
    # Buffer is usually 1000 in code, let's override logic or mock larger max_tokens if needed
    # Wait, the code has `output_buffer = 1000`. If max_tokens is 50, available is negative.
    # Let's use a larger max_tokens for the test or adjust the class behavior via mock?
    # Or just test with realistic numbers.
    
    manager.max_tokens = 3000
    
    context = "A" * 1000 # 1000 tokens
    history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Yo"}]
    
    prompt = await manager.prepare_prompt(user_input, system, context_data=context, history=history)
    
    assert "Hello world" in prompt
    assert "A" * 1000 in prompt
    assert "Hi" in prompt

@pytest.mark.asyncio
async def test_context_manager_hard_truncation():
    provider = MagicMock(spec=LLMProvider)
    async def mock_count(text):
        return len(text)
    provider.count_tokens = mock_count
    
    # Set max tokens such that context must be truncated
    # Buffer 1000. System 10. User 10. Available = Max - 1020.
    # If Max = 1500, Available = 480.
    # Context = 1000. Should truncate.
    manager = ContextManager(provider, max_tokens=1500)
    
    user_input = "User Input"
    system = "System Msg"
    context = "C" * 1000
    
    prompt = await manager.prepare_prompt(user_input, system, context_data=context)
    
    assert "User Input" in prompt
    assert "truncated" in prompt
    assert len(prompt) < 2000 # Rough check

