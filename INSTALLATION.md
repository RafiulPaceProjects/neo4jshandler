# Installation Guide

## Quick Install

### Using Docker (Recommended)

```bash
# 1. Configure
cp config/config.env.template config/config.env
nano config/config.env

# 2. Run
docker-compose up
```

### Using Python Package

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Install package
pip install -e .

# 3. Configure
cp config/config.env.template config/config.env
nano config/config.env

# 4. Run
graphbot
```

## Package Structure

The package is organized as:

```
src/graphbot/
├── __init__.py          # Package exports
├── cli.py               # CLI entry point
├── graphbot.py          # Main application
├── core/                # Core components
├── handlers/            # Database handlers
├── services/            # External services
└── utils/               # Utilities
```

## Entry Points

After installation, you can use:

- `graphbot` - Command-line interface
- `python -m graphbot.cli` - Alternative way to run

## Development Installation

```bash
# Install with development dependencies
make dev-install
# or
pip install -e ".[dev]"
```

## Troubleshooting

### Import Errors

If you get import errors, ensure:
1. Package is installed: `pip install -e .`
2. Virtual environment is activated
3. PYTHONPATH includes src: `export PYTHONPATH=$PWD/src:$PYTHONPATH`

### Command Not Found

If `graphbot` command is not found:
1. Ensure package is installed: `pip install -e .`
2. Check virtual environment is activated
3. Verify entry point: `which graphbot`

### Configuration Issues

Ensure `config/config.env` exists and contains:
- `NEO4J_PASSWORD` (required)
- `GEMINI_API_KEY` (required)
- Other settings as needed

