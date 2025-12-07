import types

from graphbot.services.insight_agent import InsightAgent


class DummyGemini:
    def __init__(self, worker_model):
        self._worker_model = worker_model

    def get_worker_model(self):
        return self._worker_model


class StubWorker:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate_content(self, prompt: str):
        self.prompts.append(prompt)
        text = self.responses.pop(0)
        return types.SimpleNamespace(text=text)


def test_generate_summary_uses_worker_model():
    worker = StubWorker(["This is a summary."])
    agent = InsightAgent(DummyGemini(worker))

    summary = agent._generate_summary("Schema text here")

    assert summary == "This is a summary."
    assert "Schema text here" in worker.prompts[0]


def test_suggest_questions_trims_and_limits():
    worker = StubWorker(
        [
            "Question one\n- Question two\n3. Question three\nQuestion four extra",
        ]
    )
    agent = InsightAgent(DummyGemini(worker))

    questions = agent._suggest_questions("schema", "summary")

    assert questions == ["Question one", "Question two", "Question three"]

