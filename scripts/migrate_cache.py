#!/usr/bin/env python3
"""
Cache Migration Script for Neo4j GraphBot.

Migrates old individual cache files to the new centralized cache format.
"""
import os
import json
import glob
import time
from pathlib import Path

from graphbot.services.cache_manager import get_cache_manager


def migrate_old_cache_files():
    """Migrate old .graphbot_cache_*.json files to centralized cache."""
    print("🔄 Starting cache migration...")

    # Find all old cache files
    cache_pattern = ".graphbot_cache_*.json"
    old_cache_files = glob.glob(cache_pattern)

    if not old_cache_files:
        print("✅ No old cache files found. Migration complete.")
        return

    print(f"Found {len(old_cache_files)} old cache files to migrate.")

    cache_manager = get_cache_manager()
    migrated_count = 0
    error_count = 0

    for cache_file in old_cache_files:
        try:
            print(f"Processing {cache_file}...")

            # Load old cache data
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)

            # Extract connection info from filename if possible
            # The old format used: .graphbot_cache_{md5(uri-database)}.json
            filename = Path(cache_file).stem
            cache_key = filename.replace('.graphbot_cache_', '')

            # For migration, we'll create a generic key based on the cache key
            # In a real scenario, you might want to store connection metadata
            migration_key = f"migrated_{cache_key}"

            # Store in new cache with current timestamp
            cache_manager.put(migration_key, cache_data)

            # Remove old file
            os.remove(cache_file)
            migrated_count += 1
            print(f"✅ Migrated {cache_file}")

        except Exception as e:
            print(f"❌ Error migrating {cache_file}: {e}")
            error_count += 1

    print(f"\n📊 Migration Summary:")
    print(f"  Migrated: {migrated_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total processed: {len(old_cache_files)}")

    if migrated_count > 0:
        print("\n⚠️  Note: Migrated cache entries use generic keys.")
        print("   You may want to clear the cache and regenerate insights")
        print("   to get proper cache keys based on database connections.")


def cleanup_orphaned_cache():
    """Clean up any orphaned cache files or temporary files."""
    print("🧹 Cleaning up orphaned cache files...")

    cleaned_count = 0

    # Remove any .tmp cache files that might be left over
    for tmp_file in glob.glob(".graphbot_cache*.tmp"):
        try:
            os.remove(tmp_file)
            cleaned_count += 1
            print(f"Removed orphaned temp file: {tmp_file}")
        except Exception as e:
            print(f"Error removing {tmp_file}: {e}")

    if cleaned_count == 0:
        print("✅ No orphaned files found.")
    else:
        print(f"🗑️  Cleaned up {cleaned_count} orphaned files.")


if __name__ == "__main__":
    print("Neo4j GraphBot Cache Migration Tool")
    print("=" * 40)

    migrate_old_cache_files()
    print()
    cleanup_orphaned_cache()

    print("\n🎉 Cache migration completed!")
