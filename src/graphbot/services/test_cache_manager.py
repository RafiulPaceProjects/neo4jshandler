"""
Tests for the centralized cache manager.
"""
import pytest
import time
import tempfile
import os
from unittest.mock import patch

from graphbot.services.cache_manager import CacheManager, create_cache_key


@pytest.fixture
def temp_cache_file():
    """Create a temporary cache file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
        temp_file = f.name
    yield temp_file
    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def cache_manager(temp_cache_file):
    """Create a cache manager with a temporary file."""
    return CacheManager(
        cache_file=temp_cache_file,
        max_age_hours=1,  # 1 hour for testing
        max_entries=10
    )


def test_cache_put_and_get(cache_manager):
    """Test basic put and get operations."""
    test_data = {"key": "value", "number": 42}

    # Put data
    cache_manager.put("test_key", test_data)

    # Get data back
    retrieved = cache_manager.get("test_key")
    assert retrieved == test_data


def test_cache_miss(cache_manager):
    """Test getting non-existent key returns None."""
    result = cache_manager.get("nonexistent")
    assert result is None


def test_cache_expiration(cache_manager):
    """Test cache expiration."""
    test_data = {"data": "expires"}

    # Put data with very short expiration (1 second ago)
    with patch('time.time', return_value=time.time() - 3601):  # 1 hour + 1 second ago
        cache_manager.put("expired_key", test_data)

    # Should return None due to expiration
    result = cache_manager.get("expired_key")
    assert result is None


def test_cache_size_limit(cache_manager):
    """Test cache size enforcement."""
    # Create cache manager with very small limit
    small_cache = CacheManager(
        cache_file=cache_manager.cache_file,
        max_age_hours=24,
        max_entries=3
    )

    # Add more items than the limit
    for i in range(5):
        small_cache.put(f"key_{i}", f"value_{i}")

    # Should only have 3 items
    stats = small_cache.get_stats()
    assert stats['total_entries'] == 3


def test_cache_invalidation(cache_manager):
    """Test cache invalidation."""
    test_data = {"data": "to_invalidate"}

    # Put data
    cache_manager.put("invalidate_key", test_data)
    assert cache_manager.get("invalidate_key") == test_data

    # Invalidate
    result = cache_manager.invalidate("invalidate_key")
    assert result is True

    # Should be gone
    assert cache_manager.get("invalidate_key") is None

    # Invalidate non-existent key
    result = cache_manager.invalidate("nonexistent")
    assert result is False


def test_cache_clear(cache_manager):
    """Test cache clearing."""
    # Add some data
    for i in range(3):
        cache_manager.put(f"clear_key_{i}", f"clear_value_{i}")

    stats = cache_manager.get_stats()
    assert stats['total_entries'] == 3

    # Clear cache
    cache_manager.clear()

    stats = cache_manager.get_stats()
    assert stats['total_entries'] == 0


def test_cache_stats(cache_manager):
    """Test cache statistics."""
    # Empty cache stats
    stats = cache_manager.get_stats()
    assert stats['total_entries'] == 0
    assert stats['total_accesses'] == 0

    # Add some data (put operations count as initial access)
    cache_manager.put("stats_key1", "stats_value1")
    time.sleep(0.01)  # Small delay for timestamp difference
    cache_manager.put("stats_key2", "stats_value2")

    # Access one item multiple times
    cache_manager.get("stats_key1")
    cache_manager.get("stats_key1")
    cache_manager.get("stats_key2")

    stats = cache_manager.get_stats()
    assert stats['total_entries'] == 2
    assert stats['total_accesses'] == 5  # 1 (put) + 2 (gets) for key1 + 1 (put) + 1 (get) for key2
    assert stats['oldest_entry'] < stats['newest_entry']


def test_cache_list_entries(cache_manager):
    """Test listing cache entries."""
    # Empty cache
    entries = cache_manager.list_entries()
    assert entries == []

    # Add entries
    cache_manager.put("list_key1", {"data": "value1"})
    cache_manager.put("list_key2", {"data": "value2"})

    # Access one to change ordering
    cache_manager.get("list_key1")

    entries = cache_manager.list_entries()
    assert len(entries) == 2

    # Should be sorted by last accessed (most recent first)
    assert entries[0]['key'] == "list_key1"  # Most recently accessed
    assert entries[1]['key'] == "list_key2"

    # Check metadata
    assert all('age_seconds' in entry for entry in entries)
    assert all('access_count' in entry for entry in entries)


def test_create_cache_key():
    """Test cache key creation."""
    key1 = create_cache_key("bolt://localhost:7687", "neo4j")
    key2 = create_cache_key("bolt://localhost:7687", "neo4j")
    key3 = create_cache_key("bolt://localhost:7687", "testdb")

    # Same inputs should produce same key
    assert key1 == key2
    # Different inputs should produce different keys
    assert key1 != key3

    # Test with context
    key4 = create_cache_key("bolt://localhost:7687", "neo4j", "insights")
    assert key4 != key1


def test_cache_persistence(temp_cache_file):
    """Test cache persistence across instances."""
    # Create first manager and add data
    manager1 = CacheManager(cache_file=temp_cache_file, max_age_hours=24)
    test_data = {"persistent": "data", "number": 123}
    manager1.put("persistent_key", test_data)

    # Create second manager with same file
    manager2 = CacheManager(cache_file=temp_cache_file, max_age_hours=24)

    # Should be able to retrieve data
    retrieved = manager2.get("persistent_key")
    assert retrieved == test_data


def test_cache_cleanup(cache_manager):
    """Test cache cleanup functionality."""
    # Add a valid entry
    cache_manager.put("valid_key", "valid_data")

    # Manually create an expired entry by manipulating the cache directly
    from graphbot.services.cache_manager import CacheEntry
    expired_entry = CacheEntry(
        key="expired_key",
        data="expired_data",
        timestamp=time.time() - 7200,  # 2 hours ago
        access_count=1,
        last_accessed=time.time() - 7200
    )
    cache_manager._cache["expired_key"] = expired_entry

    # Should have 2 entries initially
    assert len(cache_manager._cache) == 2

    # Run cleanup - this should remove expired entries
    cache_manager.cleanup()

    # Should only have 1 valid entry
    stats = cache_manager.get_stats()
    assert stats['total_entries'] == 1

    # Valid entry should still be there
    assert cache_manager.get("valid_key") == "valid_data"
    # Expired entry should be gone
    assert cache_manager.get("expired_key") is None
