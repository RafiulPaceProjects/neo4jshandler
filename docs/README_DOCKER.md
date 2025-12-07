# Docker Deployment Guide

This guide details how to run Neo4j GraphBot using Docker and Docker Compose.

## 🐳 Quick Start with Compose

The easiest way to run the bot is using `docker-compose`.

1. **Configure**:
   Ensure `config/config.env` exists and is populated.
   ```bash
   cp config/config.env.template config/config.env
   nano config/config.env
   ```

2. **Run**:
   ```bash
   docker-compose up
   ```

   To run in the background (detached):
   ```bash
   docker-compose up -d
   ```

## 🌐 Networking

The `docker-compose.yml` uses `network_mode: host`. This allows the container to share the host's network stack, making it easy to connect to a local Neo4j instance running on the host machine using `localhost:7687`.

**Note for Mac/Windows**: `host` networking has limitations on Docker Desktop. If you cannot connect to `localhost`, try using `host.docker.internal` in your `NEO4J_URI`.

## 🔧 Environment Overrides

You can override configuration settings directly via environment variables without editing the file. This is useful for CI/CD or temporary changes.

```bash
# Example: Run with a specific database and model
NEO4J_DATABASE=production_db \
MAIN_MODEL=gemini-2.0-flash \
docker-compose up
```

## 📦 Building Manually

If you prefer to build the image yourself:

```bash
# Build
docker build -t neo4j-graphbot .

# Run (mounting config)
docker run -it --rm \
  --network host \
  -v $(pwd)/config/config.env:/app/config/config.env:ro \
  neo4j-graphbot
```

## 🛡️ Production Considerations

1. **Secrets**: Do not commit `config.env` to version control.
2. **Read-Only Config**: The container mounts the config file as read-only (`:ro`).
3. **Logs**: View logs using `docker-compose logs -f`.
4. **Health Checks**: The current image assumes the application runs interactively. For headless deployment, you may need to adapt the entrypoint.

## 🐛 Troubleshooting Docker

**"Connection Refused" to Neo4j**
- Ensure Neo4j is running.
- If Neo4j is on the host:
    - **Linux**: `localhost` works with `--network host`.
    - **Mac/Windows**: Use `neo4j://host.docker.internal:7687`.

**"Config file not found"**
- The container expects the config file at `/app/config/config.env`.
- Ensure you have mounted it correctly: `-v $(pwd)/config/config.env:/app/config/config.env:ro`.
