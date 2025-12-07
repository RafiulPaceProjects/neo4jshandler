"""
Neo4j GraphBot - A CLI interface for interacting with Neo4j using natural language.

A production-ready application that allows users to interact with their Neo4j
graph database using natural language queries powered by Google's Gemini API.
"""

__version__ = "1.0.0"
__author__ = "Rafiul Haider"

from .graphbot import GraphBot

__all__ = ["GraphBot"]

