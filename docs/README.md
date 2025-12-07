# Neo4j GraphBot

A production-ready Python CLI application that allows you to interact with your Neo4j graph database using natural language. Powered by Google's Gemini API for intelligent query generation.

## Features

- 🤖 Natural language to Cypher query conversion via Gemini API
- 🔍 Full CRUD operations (Create, Read, Update, Delete)
- 🎨 Beautiful CLI interface with Rich library
- ✅ Query validation and safety checks
- 📊 Formatted result display
- 🔒 Confirmation prompts for write operations
- 🐳 Docker support for easy deployment
- 📦 Modular, production-ready codebase

## Project Structure

```
neo4jsinteract/
├── src/
│   └── graphbot/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point
│       ├── graphbot.py         # Main application class
│       ├── core/               # Core components
│       │   ├── __init__.py
│       │   └── schema_context.py
│       ├── handlers/           # Database handlers
│       │   ├── __init__.py
│       │   └── neo4j_handler.py
│       ├── services/           # External services
│       │   ├── __init__.py
│       │   └── gemini_service.py
│       └── utils/              # Utilities
│           ├── __init__.py
│           └── query_builder.py
├── config/                     # Configuration files
│   ├── config.env.template     # Template (safe to commit)
│   └── config.env              # User config (gitignored)
├── scripts/                    # Utility scripts
│   ├── explore_database.py
│   ├── explore_database_simple.py
│   └── test_connection.py
├── docs/                       # Documentation
│   ├── README.md
│   ├── README_DOCKER.md
│   └── QUICKSTART.md
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── setup.py
├── requirements.txt
├── Makefile
└── run.sh
```

## Quick Start

### Option 1: Docker (Recommended)

1. **Edit configuration:**
   ```bash
   cp config/config.env.template config/config.env
   nano config/config.env
   ```

2. **Run:**
   ```bash
   docker-compose up
   ```

See [QUICKSTART.md](QUICKSTART.md) for more details.

### Option 2: Local Installation

1. **Install:**
   ```bash
   pip install -e .
   ```

2. **Configure:**
   ```bash
   cp config/config.env.template config/config.env
   nano config/config.env
   ```

3. **Run:**
   ```bash
   graphbot
   # or
   python -m graphbot.cli
   ```

## Configuration

Edit `config/config.env` with your credentials:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=your_database
GEMINI_API_KEY=your_api_key
```

## Development

```bash
# Install with dev dependencies
make dev-install

# Run tests
make test

# Format code
make format

# Lint code
make lint
```

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [README_DOCKER.md](README_DOCKER.md) - Docker setup guide
- [README.md](README.md) - This file

## License

MIT License
