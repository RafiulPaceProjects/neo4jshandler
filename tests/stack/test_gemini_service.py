import types

import pytest

from graphbot.services.gemini_service import GeminiService


class FakeResponse:
    def __init__(self, text: str):
        self.text = text
        self.parts = [types.SimpleNamespace(text=text)]


class FakeModelInfo:
    def __init__(self, name: str):
        self.name = f"models/{name}"
        self.supported_generation_methods = ["generateContent"]


@pytest.fixture
def stub_genai(monkeypatch):
    class FakeModel:
        def __init__(self, name: str):
            self.name = name
            self._next_response = FakeResponse("DEFAULT")
            self.last_prompt = None

        def generate_content(self, prompt: str):
            self.last_prompt = prompt
            return self._next_response

    def fake_list_models():
        return [
            FakeModelInfo("gemini-3-pro-preview"),
            FakeModelInfo("gemini-1.5-flash"),
        ]

    monkeypatch.setenv("GEMINI_API_KEY", "AIza" + "A" * 30)
    monkeypatch.setenv("MAIN_MODEL", "gemini-3-pro-preview")
    monkeypatch.setenv("WORKER_MODEL", "gemini-1.5-flash")
    monkeypatch.setattr("graphbot.services.gemini_service.genai.configure", lambda api_key: None)
    monkeypatch.setattr("graphbot.services.gemini_service.genai.list_models", fake_list_models)
    monkeypatch.setattr("graphbot.services.gemini_service.genai.GenerativeModel", FakeModel)
    return FakeModel


def test_generate_cypher_query_returns_plain_text(stub_genai):
    service = GeminiService()
    service.main_model._next_response = FakeResponse("MATCH (n) RETURN n LIMIT 25")

    query = service.generate_cypher_query("Find all nodes")

    assert query == "MATCH (n) RETURN n LIMIT 25"
    assert "Find all nodes" in service.main_model.last_prompt


def test_generate_cypher_query_strips_markdown_code_block(stub_genai):
    service = GeminiService()
    service.main_model._next_response = FakeResponse("```cypher\nMATCH (n)\nRETURN n\n```")

    query = service.generate_cypher_query("Use markdown")

    assert query == "MATCH (n)\nRETURN n"

