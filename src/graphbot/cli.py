#!/usr/bin/env python3
"""
Command-line interface entry point for GraphBot.

This module provides the main entry point for running GraphBot from the command line.
"""

import sys
from graphbot import GraphBot


def main():
    """Main entry point for the CLI application."""
    bot = GraphBot()
    bot.run()


if __name__ == "__main__":
    main()

