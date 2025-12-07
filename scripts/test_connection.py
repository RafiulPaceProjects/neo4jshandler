#!/usr/bin/env python3
"""Test script to diagnose Neo4j connection issues."""
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables from .env or config.env
load_dotenv()
config_file = os.getenv("CONFIG_FILE", "config/config.env")
if os.path.exists(config_file):
    load_dotenv(config_file)

uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD")

print(f"Testing connection with:")
print(f"  URI: {uri}")
print(f"  User: {user}")
print(f"  Password: {'*' * len(password) if password else 'NOT SET'}")
print()

if not password:
    print("ERROR: NEO4J_PASSWORD is not set!")
    exit(1)

# Try different URI schemes
uris_to_try = [
    uri,
    uri.replace("neo4j://", "bolt://"),
    uri.replace("127.0.0.1", "localhost"),
    uri.replace("neo4j://127.0.0.1", "bolt://localhost"),
]

for test_uri in uris_to_try:
    print(f"Trying: {test_uri}")
    try:
        driver = GraphDatabase.driver(test_uri, auth=(user, password))
        driver.verify_connectivity()
        print(f"✓ SUCCESS! Connected using: {test_uri}")
        
        # Test a simple query
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            print(f"✓ Query test successful: {record['test']}")
        
        driver.close()
        print(f"\nUse this URI in your .env file: {test_uri}")
        break
    except Exception as e:
        print(f"✗ Failed: {str(e)}")
        print()
else:
    print("\nAll connection attempts failed.")
    print("\nTroubleshooting tips:")
    print("1. Make sure Neo4j is running")
    print("2. Verify your password is correct")
    print("3. Check if Neo4j is listening on port 7687")
    print("4. Try connecting via Neo4j Browser first to verify credentials")

