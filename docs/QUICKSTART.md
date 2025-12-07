# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Edit Configuration

Edit the `config.env` file with your credentials:

```bash
# Open the config file
nano config.env
```

Fill in:
- `NEO4J_URI` - Your Neo4j connection (e.g., `bolt://localhost:7687`)
- `NEO4J_USER` - Your Neo4j username (usually `neo4j`)
- `NEO4J_PASSWORD` - Your Neo4j password ⚠️ **REQUIRED**
- `NEO4J_DATABASE` - Your database name (leave empty for default)
- `GEMINI_API_KEY` - Your Gemini API key ⚠️ **REQUIRED**

### Step 2: Run with Docker

```bash
docker-compose up
```

That's it! The bot will start and connect to your Neo4j database.

### Step 3: Start Querying

Once started, you can ask questions like:
- "Show me all nodes"
- "Count claims by type"
- "Find all fraudulent providers"

## 📝 Example config.env

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mypassword123
NEO4J_DATABASE=healthproject

# Gemini API
GEMINI_API_KEY=AIzaSyDmDwfCwQnbwKqB96wHQU4qLc2tIEoZMYU
```

## 🔧 Connection Examples

### Local Neo4j
```bash
NEO4J_URI=bolt://localhost:7687
```

### Neo4j on Docker Host
```bash
NEO4J_URI=bolt://host.docker.internal:7687
```

### Remote Neo4j Server
```bash
NEO4J_URI=bolt://your-server.com:7687
```

## ❓ Need Help?

- See [README.md](README.md) for full documentation
- See [README_DOCKER.md](README_DOCKER.md) for Docker details
- Check that your Neo4j is running and accessible
- Verify your API key at https://makersuite.google.com/app/apikey

