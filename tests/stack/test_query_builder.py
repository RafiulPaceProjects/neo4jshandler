import pytest

from graphbot.utils.query_builder import QueryBuilder


@pytest.mark.parametrize(
    "query",
    [
        "DROP DATABASE mydb",
        "drop index ON :Person(name)",
        "DROP CONSTRAINT something",
        "MATCH (n) DETACH DELETE n",
    ],
)
def test_validate_query_blocks_dangerous_operations(query):
    is_valid, error = QueryBuilder.validate_query(query)
    assert is_valid is False
    assert "dangerous" in error.lower()


def test_validate_query_requires_cypher_keyword():
    is_valid, error = QueryBuilder.validate_query("some random text without cypher")
    assert is_valid is False
    assert "cypher keyword" in error.lower()


def test_sanitize_query_strips_comments_and_spaces():
    raw = "MATCH (n) // comment here\nRETURN n  // trailing"
    sanitized = QueryBuilder.sanitize_query(raw)
    assert sanitized == "MATCH (n) RETURN n"


def test_is_read_only_detects_writes():
    assert QueryBuilder.is_read_only("MATCH (n) RETURN n") is True
    assert QueryBuilder.is_read_only("MATCH (n) DELETE n") is False

