import pytest

from graphbot.handlers.neo4j_handler import Neo4jHandler


class FakeNode(dict):
    def __init__(self, node_id, labels, props):
        super().__init__(props)
        self.id = node_id
        self.labels = set(labels)


class FakeRelationship(dict):
    def __init__(self, rel_id, rel_type, start, end, props):
        super().__init__(props)
        self.id = rel_id
        self.type = rel_type
        self.start_node = type("NodeRef", (), {"id": start})
        self.end_node = type("NodeRef", (), {"id": end})


class FakeRecord:
    def __init__(self, data):
        self._data = data

    def keys(self):
        return self._data.keys()

    def __getitem__(self, item):
        return self._data[item]


class FakeResult:
    def __init__(self, records):
        self._records = records

    def __iter__(self):
        return iter(self._records)

    def single(self):
        return self._records[0]


class FakeSession:
    def __init__(self, result=None, exc=None):
        self._result = result
        self._exc = exc

    def run(self, query, parameters=None):
        if self._exc:
            raise self._exc
        return self._result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class FakeDriver:
    def __init__(self, session):
        self._session = session

    def session(self, database=None):
        return self._session

    def verify_connectivity(self):
        return True

    def close(self):
        pass


@pytest.fixture
def handler(monkeypatch):
    monkeypatch.setenv("NEO4J_PASSWORD", "password")
    monkeypatch.setattr(Neo4jHandler, "_connect", lambda self: None)
    neo = Neo4jHandler()
    neo.database = "neo4j"
    return neo


def test_execute_query_transforms_records(handler):
    record = FakeRecord(
        {
            "n": FakeNode(1, ["Person"], {"name": "Alice"}),
            "r": FakeRelationship(2, "KNOWS", 1, 2, {"since": 2020}),
            "value": 5,
        }
    )
    handler.driver = FakeDriver(FakeSession(result=FakeResult([record])))

    results = handler.execute_query("MATCH (n)-[r]->(m) RETURN n, r, 5 as value")

    assert results[0]["n"]["type"] == "Node"
    assert set(results[0]["n"]["labels"]) == {"Person"}
    assert results[0]["r"]["type"] == "Relationship"
    assert results[0]["r"]["type_name"] == "KNOWS"
    assert results[0]["value"] == 5


def test_execute_query_raises_on_failure(handler):
    handler.driver = FakeDriver(FakeSession(exc=RuntimeError("db down")))

    with pytest.raises(RuntimeError):
        handler.execute_query("MATCH (n) RETURN n")

