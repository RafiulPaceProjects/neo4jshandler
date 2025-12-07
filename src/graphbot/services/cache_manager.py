"""
Centralized Cache Management for Neo4j GraphBot.

Provides thread-safe caching with expiration, size limits, and management capabilities.
"""
import os
import json
import time
import hashlib
import threading
from typing import Any, Optional
from dataclasses import dataclass
from rich.console import Console

console = Console()


@dataclass
class CacheEntry:
    """Represents a cached item with metadata."""
    key: str
    data: Any
    timestamp: float
    access_count: int = 0
    last_accessed: float = 0.0

    def is_expired(self, max_age: int) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.timestamp > max_age

    def touch(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()


class CacheManager:
    """
    Centralized cache manager with expiration, size limits, and thread safety.
    """

    def __init__(self, cache_file: str = ".graphbot_cache.json",
                 max_age_hours: int = 24,
                 max_entries: int = 100):
        """
        Initialize cache manager.

        Args:
            cache_file: Path to cache file
            max_age_hours: Maximum age of cache entries in hours
            max_entries: Maximum number of cache entries
        """
        self.cache_file = cache_file
        self.max_age_seconds = max_age_hours * 3600
        self.max_entries = max_entries
        self._lock = threading.RLock()
        self._dirty = False
        self._cache: dict[str, CacheEntry] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cache from file."""
        if not os.path.exists(self.cache_file):
            return

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Reconstruct CacheEntry objects
            for key, entry_data in data.get('entries', {}).items():
                self._cache[key] = CacheEntry(
                    key=key,
                    data=entry_data['data'],
                    timestamp=entry_data['timestamp'],
                    access_count=entry_data.get('access_count', 0),
                    last_accessed=entry_data.get('last_accessed', entry_data['timestamp'])
                )

            console.print(f"[dim]Loaded {len(self._cache)} cache entries from {self.cache_file}[/dim]")

        except Exception as e:
            console.print(f"[yellow]Warning: Could not load cache file {self.cache_file}: {e}[/yellow]")
            # Start with empty cache if file is corrupted
            self._cache = {}

    def _save_cache(self):
        """Save cache to file."""
        try:
            # Convert CacheEntry objects to serializable dicts
            entries = {}
            for key, entry in self._cache.items():
                entries[key] = {
                    'data': entry.data,
                    'timestamp': entry.timestamp,
                    'access_count': entry.access_count,
                    'last_accessed': entry.last_accessed
                }

            data = {
                'version': '1.0',
                'created': time.time(),
                'entries': entries
            }

            # Write to temporary file first, then rename for atomicity
            temp_file = self.cache_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            os.rename(temp_file, self.cache_file)
            self._dirty = False

        except Exception as e:
            console.print(f"[yellow]Warning: Could not save cache file {self.cache_file}: {e}[/yellow]")

    def _cleanup_expired(self):
        """Remove expired entries."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired(self.max_age_seconds)
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            console.print(f"[dim]Cleaned up {len(expired_keys)} expired cache entries[/dim]")

    def _enforce_size_limit(self):
        """Enforce maximum cache size using LRU eviction."""
        if len(self._cache) <= self.max_entries:
            return

        # Sort by last accessed time (oldest first)
        entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed
        )

        # Remove oldest entries
        to_remove = len(self._cache) - self.max_entries
        removed_keys = []

        for key, _ in entries[:to_remove]:
            del self._cache[key]
            removed_keys.append(key)

        if removed_keys:
            console.print(f"[dim]Evicted {len(removed_keys)} cache entries due to size limit[/dim]")

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve item from cache.

        Args:
            key: Cache key

        Returns:
            Cached data or None if not found/expired
        """
        with self._lock:
            self._cleanup_expired()

            entry = self._cache.get(key)
            if entry and not entry.is_expired(self.max_age_seconds):
                entry.touch()
                return entry.data
            elif entry:
                # Remove expired entry
                del self._cache[key]

            return None

    def put(self, key: str, data: Any):
        """
        Store item in cache.

        Args:
            key: Cache key
            data: Data to cache
        """
        with self._lock:
            self._cleanup_expired()

            entry = CacheEntry(
                key=key,
                data=data,
                timestamp=time.time()
            )
            entry.touch()

            self._cache[key] = entry
            self._enforce_size_limit()
            self._dirty = True
            # self._save_cache() # Optimized: Don't save on every put

    def invalidate(self, key: str) -> bool:
        """
        Remove specific item from cache.

        Args:
            key: Cache key to remove

        Returns:
            True if item was removed, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._save_cache()
                return True
            return False

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._save_cache()
            console.print("[dim]Cache cleared[/dim]")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            self._cleanup_expired()

            total_entries = len(self._cache)
            if total_entries == 0:
                return {
                    'total_entries': 0,
                    'oldest_entry': None,
                    'newest_entry': None,
                    'average_age': 0,
                    'total_accesses': 0
                }

            timestamps = [entry.timestamp for entry in self._cache.values()]
            access_counts = [entry.access_count for entry in self._cache.values()]

            return {
                'total_entries': total_entries,
                'oldest_entry': min(timestamps),
                'newest_entry': max(timestamps),
                'average_age': time.time() - sum(timestamps) / len(timestamps),
                'total_accesses': sum(access_counts)
            }

    def list_entries(self) -> list[dict[str, Any]]:
        """List all cache entries with metadata."""
        with self._lock:
            self._cleanup_expired()

            entries = []
            for key, entry in self._cache.items():
                entries.append({
                    'key': key,
                    'age_seconds': time.time() - entry.timestamp,
                    'access_count': entry.access_count,
                    'last_accessed': entry.last_accessed,
                    'data_size': len(json.dumps(entry.data)) if entry.data else 0
                })

            # Sort by last accessed (most recent first)
            return sorted(entries, key=lambda x: x['last_accessed'], reverse=True)

    def cleanup(self):
        """Perform maintenance cleanup."""
        with self._lock:
            old_count = len(self._cache)
            self._cleanup_expired()
            self._enforce_size_limit()
            new_count = len(self._cache)

            if old_count != new_count or self._dirty:
                self._save_cache()
                console.print(f"[dim]Cache maintenance: {old_count} → {new_count} entries[/dim]")

    def save_if_dirty(self):
        """Save cache to disk if modified."""
        with self._lock:
            if self._dirty:
                self._save_cache()


# Global cache manager instance
_cache_manager = None
_cache_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager

    if _cache_manager is None:
        with _cache_lock:
            if _cache_manager is None:
                _cache_manager = CacheManager()

    return _cache_manager


def create_cache_key(uri: str, database: str, context: str = "") -> str:
    """
    Create a standardized cache key.

    Args:
        uri: Database URI
        database: Database name
        context: Additional context (e.g., 'schema', 'insights')

    Returns:
        Cache key string
    """
    key_parts = [uri, database]
    if context:
        key_parts.append(context)

    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()
