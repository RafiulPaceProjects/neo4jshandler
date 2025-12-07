from types import SimpleNamespace

from graphbot.core.schema_context import SchemaContext


class FakeNode(dict):
    def __init__(self, node_id, labels, props):
        super().__init__(props)
        self.id = node_id
        self.labels = labels


class FakeResult:
    def __init__(self, records):
        self._records = records

    def __iter__(self):
        return iter(self._records)

    def single(self):
        return self._records[0]


class FakeSession:
    def run(self, query):
        if "RETURN DISTINCT labels" in query:
            return FakeResult([{"labels": ["Person"]}])
        if "RETURN DISTINCT type(r)" in query:
            return FakeResult([{"type": "KNOWS"}])
        if "RETURN n LIMIT 3" in query:
            return FakeResult([{"n": FakeNode(1, ["Person"], {"name": "Alice", "age": 30})}])
        if "RETURN count(n) as count" in query:
            return FakeResult([{"count": 2}])
        if "RETURN count(r) as count" in query:
            return FakeResult([{"count": 4}])
        if "RETURN DISTINCT labels(a)[0]" in query:
            return FakeResult([{"from_label": "Person", "to_label": "Person"}])
        return FakeResult([])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class FakeDriver:
    def session(self, database=None):
        return FakeSession()


def test_set_insights_populates_cache():
    handler = SimpleNamespace(driver=None, database="neo4j")
    ctx = SchemaContext(handler)

    ctx.set_insights({"summary": "Tiny graph", "raw_schema": "(A)-[:R]->(B)"})

    schema_text = ctx.get_schema_context()
    assert "Tiny graph" in schema_text
    assert "(A)-[:R]->(B)" in schema_text


def test_generate_legacy_schema_uses_driver():
    handler = SimpleNamespace(driver=FakeDriver(), database="neo4j")
    ctx = SchemaContext(handler)

    schema_text = ctx.get_schema_context()

    assert "Person" in schema_text
    assert "KNOWS" in schema_text

