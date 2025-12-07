# Project Structure

This document describes the modular, production-ready structure of Neo4j GraphBot.

## Directory Layout

```
neo4jsinteract/
├── src/                          # Source code
│   └── graphbot/                 # Main package
│       ├── __init__.py           # Package initialization
│       ├── cli.py                # CLI entry point
│       ├── graphbot.py           # Main application class
│       ├── core/                 # Core components
│       │   ├── __init__.py
│       │   └── schema_context.py # Database schema context
│       ├── handlers/             # Database handlers
│       │   ├── __init__.py
│       │   └── neo4j_handler.py  # Neo4j connection & queries
│       ├── services/             # External service integrations
│       │   ├── __init__.py
│       │   └── gemini_service.py # Gemini API integration
│       └── utils/                # Utility functions
│           ├── __init__.py
│           └── query_builder.py # Query validation & sanitization
│
├── config/                       # Configuration files
│   ├── config.env.template       # Template (safe to commit)
│   └── config.env                # User config (gitignored)
│
├── scripts/                      # Utility scripts
│   ├── explore_database.py       # Database exploration tool
│   ├── explore_database_simple.py # Simplified exploration
│   └── test_connection.py       # Connection testing tool
│
├── docs/                         # Documentation
│   ├── README.md                 # Full documentation
│   ├── README_DOCKER.md          # Docker setup guide
│   └── QUICKSTART.md             # Quick start guide
│
├── Dockerfile                    # Docker image definition
├── docker-compose.yml            # Docker Compose configuration
├── pyproject.toml                 # Modern Python packaging (PEP 621)
├── setup.py                      # Setuptools configuration
├── requirements.txt              # Python dependencies
├── Makefile                      # Development commands
├── run.sh                        # Convenience run script
├── README.md                     # Main README
├── .gitignore                    # Git ignore rules
└── .dockerignore                 # Docker ignore rules
```

## Module Organization

### `graphbot.core`
Core business logic and domain models.

- **schema_context.py**: Manages database schema information for context-aware query generation

### `graphbot.handlers`
Database connection and query execution handlers.

- **neo4j_handler.py**: Handles Neo4j database connections, query execution, and result formatting

### `graphbot.services`
External service integrations.

- **gemini_service.py**: Google Gemini API integration for natural language processing

### `graphbot.utils`
Utility functions and helper classes.

- **query_builder.py**: Query validation, sanitization, and safety checks

### `graphbot`
Main application logic.

- **graphbot.py**: Main GraphBot application class
- **cli.py**: Command-line interface entry point

## Configuration

All configuration is centralized in `config/config.env`:

- Neo4j connection settings
- Gemini API credentials
- Database name

## Scripts

Utility scripts in `scripts/` for:
- Database exploration
- Connection testing
- Development tasks

## Documentation

All documentation is in `docs/`:
- Main README
- Docker guide
- Quick start guide

## Benefits of This Structure

1. **Modularity**: Clear separation of concerns
2. **Maintainability**: Easy to find and modify code
3. **Testability**: Each module can be tested independently
4. **Scalability**: Easy to add new features
5. **Production-ready**: Follows Python packaging best practices
6. **Docker-friendly**: Clean structure for containerization

## Import Examples

```python
# From within the package
from graphbot.handlers import Neo4jHandler
from graphbot.services import GeminiService
from graphbot.utils import QueryBuilder
from graphbot.core import SchemaContext

# Main application
from graphbot import GraphBot
```

