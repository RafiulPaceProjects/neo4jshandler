# Quick Start Guide

This guide will get you up and running with Neo4j GraphBot in minutes.

## Prerequisites

1. **Neo4j Database**: You need a running Neo4j instance.
   - [Neo4j Desktop](https://neo4j.com/download/) (Local)
   - [Neo4j Aura](https://neo4j.com/cloud/aura/) (Cloud)
   - Docker container (`docker run -p 7474:7474 -p 7687:7687 neo4j`)

2. **Gemini API Key**:
   - Get a key from [Google AI Studio](https://makersuite.google.com/app/apikey).

## Installation

### Method 1: Docker (Recommended)

This method ensures you have all dependencies isolated.

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone <repo-url>
   cd neo4jsinteract
   ```

2. **Setup Configuration**:
   ```bash
   cp config/config.env.template config/config.env
   ```
   
   Edit `config/config.env`:
   - Set `NEO4J_URI` (e.g., `neo4j://host.docker.internal:7687` for local DB accessed from Docker)
   - Set `NEO4J_PASSWORD`
   - Set `GEMINI_API_KEY`

3. **Run**:
   ```bash
   docker-compose up
   ```
   The container will start and you can interact with the bot in the terminal.

### Method 2: Local Python Environment

Use this if you want to develop or run directly on your host machine.

1. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install Package**:
   ```bash
   pip install -e .
   ```

3. **Configure**:
   ```bash
   cp config/config.env.template config/config.env
   # Edit config.env with your credentials
   ```

4. **Run**:
   ```bash
   graphbot
   ```

## Configuration Reference

The `config.env` file supports the following variables:

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `NEO4J_URI` | No | `neo4j://localhost:7687` | Connection URI |
| `NEO4J_USER` | No | `neo4j` | Database username |
| `NEO4J_PASSWORD` | **Yes** | - | Database password |
| `NEO4J_DATABASE` | No | `healthproject`* | Target database name |
| `GEMINI_API_KEY` | **Yes** | - | Google AI API Key |
| `MAIN_MODEL` | No | `gemini-3-pro-preview` | Model for query generation |
| `WORKER_MODEL` | No | `gemini-2.0-flash` | Model for background tasks |

*> Note: The code currently defaults to `healthproject` if not specified. We recommend explicitly setting this to `neo4j` or your specific database name.*

## Troubleshooting

- **Connection Refused**: If running in Docker and connecting to localhost Neo4j, use `host.docker.internal` instead of `localhost`.
- **Authentication Failed**: Check your Neo4j password.
- **API Errors**: Verify your Gemini API key has active quota.
