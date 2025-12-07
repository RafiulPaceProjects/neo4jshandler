# Neo4j GraphBot

A production-ready Python CLI application that allows you to interact with **any** Neo4j graph database using natural language. Whether you're working with finance, healthcare, social networks, or any other domain, GraphBot intelligently adapts to your schema. Powered by Google's Gemini API for intelligent query generation.

## 🚀 Quick Start

1. **Edit configuration:**
   ```bash
   cp config/config.env.template config/config.env
   nano config/config.env
   ```

2. **Run with Docker:**
   ```bash
   docker-compose up
   ```

That's it! See [docs/QUICKSTART.md](docs/QUICKSTART.md) for more details.

## 🔌 Connecting to Your Database

GraphBot supports connecting to any Neo4j instance (Local, AuraDB, or Enterprise).

### Interactive Mode
You can switch databases directly from the CLI:
1. Start GraphBot: `graphbot`
2. Type `connect`
3. Enter your connection details:
   - URI (e.g., `bolt://localhost:7687` or `neo4j+s://your-instance.databases.neo4j.io`)
   - Username
   - Password
   - Database (optional)

### Environment Variables
You can also set default connection details in `config/config.env`:
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=your_database  # Optional, defaults to default DB
```

## 📁 Project Structure

```
neo4jsinteract/
├── src/graphbot/          # Main application package
│   ├── core/              # Core components (schema context)
│   ├── handlers/          # Database handlers (Neo4j)
│   ├── services/          # External services (Gemini API)
│   ├── utils/             # Utilities (query builder)
│   ├── cli.py             # CLI entry point
│   └── graphbot.py        # Main application class
├── config/                # Configuration files
│   ├── config.env.template
│   └── config.env         # User config (gitignored)
├── scripts/               # Utility scripts
├── docs/                  # Documentation
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker Compose configuration
├── pyproject.toml         # Modern Python packaging
├── setup.py               # Setuptools configuration
└── Makefile              # Development commands
```

## 📚 Documentation

- **[QUICKSTART.md](docs/QUICKSTART.md)** - Get started in 3 steps
- **[README_DOCKER.md](docs/README_DOCKER.md)** - Complete Docker guide
- **[README.md](docs/README.md)** - Full documentation

## 🛠️ Installation

### Docker (Recommended)

```bash
docker-compose up
```

### Local Installation

```bash
pip install -e .
graphbot
```

## ⚙️ Configuration

Edit `config/config.env`:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=your_database
GEMINI_API_KEY=your_api_key
```

## 🧪 Development

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

## 📦 Features

- 🤖 Natural language to Cypher query conversion
- 🔍 Full CRUD operations
- 🎨 Beautiful CLI interface
- ✅ Query validation and safety checks
- 📊 Formatted result display
- 🐳 Docker support
- 📦 Modular, production-ready codebase

## 📄 License

MIT License
