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
    assert sanitized == "MATCH (n) RETURN n LIMIT 100"

def test_is_read_only_detects_writes():
    assert QueryBuilder.is_read_only("MATCH (n) RETURN n") is True
    assert QueryBuilder.is_read_only("MATCH (n) DELETE n") is False
    assert QueryBuilder.is_read_only("CREATE (n)") is False
    assert QueryBuilder.is_read_only("MERGE (n)") is False
    assert QueryBuilder.is_read_only("SET n.prop = 1") is False

def test_format_query_for_display():
    raw = "MATCH (n) RETURN n"
    formatted = QueryBuilder.format_query_for_display(raw)
    assert "\nMATCH" in formatted or "MATCH" in formatted # implementation detail check
    # Check that spaces are normalized
    assert "(n) RETURN n" in formatted or "(n) \nRETURN n" in formatted


def test_validate_query_empty_input():
    """Test validation of empty or whitespace-only queries."""
    is_valid, error = QueryBuilder.validate_query("")
    assert is_valid is False
    assert "empty" in error.lower()

    is_valid, error = QueryBuilder.validate_query("   \n\t   ")
    assert is_valid is False
    assert "empty" in error.lower()


def test_validate_query_case_insensitive_keywords():
    """Test that validation is case-insensitive for Cypher keywords."""
    is_valid, error = QueryBuilder.validate_query("match (n) return n")
    assert is_valid is True

    is_valid, error = QueryBuilder.validate_query("MATCH (n) RETURN n")
    assert is_valid is True


def test_validate_query_malformed_cypher():
    """Test validation of syntactically incorrect Cypher."""
    # Note: Current validation only checks for keywords and dangerous patterns,
    # not full syntax validation. This test documents current behavior.
    is_valid, error = QueryBuilder.validate_query("MATCH (n RETURN n")  # Missing closing paren
    # Should pass basic validation since it contains MATCH and RETURN keywords
    assert is_valid is True


def test_sanitize_query_preserves_valid_structure():
    """Test that sanitization preserves valid query structure."""
    raw = "MATCH (n:Person {name: 'Alice'})-[:KNOWS]->(m:Person) RETURN n, m"
    sanitized = QueryBuilder.sanitize_query(raw)
    assert "MATCH (n:Person {name: 'Alice'})-[:KNOWS]->(m:Person) RETURN n, m LIMIT 100" == sanitized


def test_sanitize_query_handles_none_input():
    """Test sanitization of None input."""
    sanitized = QueryBuilder.sanitize_query(None)
    assert sanitized == ""


def test_sanitize_query_removes_multiple_comments():
    """Test removal of multiple comments."""
    raw = "// First comment\nMATCH (n) // inline comment\nRETURN n // final comment"
    sanitized = QueryBuilder.sanitize_query(raw)
    assert "//" not in sanitized
    assert "MATCH (n) RETURN n LIMIT 100" == sanitized


def test_is_read_only_complex_queries():
    """Test read-only detection for complex queries."""
    # Read-only queries
    assert QueryBuilder.is_read_only("MATCH (n)-[r]->(m) RETURN n, r, m") is True
    assert QueryBuilder.is_read_only("MATCH (n) WHERE n.active = true RETURN count(n)") is True

    # Write queries
    assert QueryBuilder.is_read_only("MATCH (n) SET n.updated = true") is False
    assert QueryBuilder.is_read_only("MATCH (n) REMOVE n.prop") is False
    assert QueryBuilder.is_read_only("MATCH (n) DELETE n") is False


def test_is_read_only_case_insensitive():
    """Test that read-only detection is case-insensitive."""
    assert QueryBuilder.is_read_only("match (n) return n") is True
    assert QueryBuilder.is_read_only("MATCH (n) SET n.prop = 1") is False


def test_format_query_for_display_edge_cases():
    """Test formatting with edge cases."""
    # Empty query
    formatted = QueryBuilder.format_query_for_display("")
    assert formatted == ""

    # None input
    formatted = QueryBuilder.format_query_for_display(None)
    assert formatted == ""

    # Query with excessive whitespace
    raw = "MATCH    (n)    RETURN    n"
    formatted = QueryBuilder.format_query_for_display(raw)
    assert "   " not in formatted  # Should normalize spaces

