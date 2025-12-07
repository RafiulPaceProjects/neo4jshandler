# Neo4j GraphBot - Docker Setup

This guide explains how to run the Neo4j GraphBot using Docker, connecting to your external Neo4j database.

## Quick Start (Easiest Method)

### 1. Edit the Configuration File

Simply edit the `config.env` file with your credentials:

```bash
# Open and edit the config file
nano config.env
# or
vim config.env
# or use any text editor
```

**Example `config.env`:**
```bash
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
NEO4J_DATABASE=your_database_name

# Gemini API
GEMINI_API_KEY=your_api_key_here
```

### 2. Run with Docker Compose

```bash
# Build and run
docker-compose up
```

That's it! The container will automatically load your configuration from `config.env`.

### 3. Run with Docker (Alternative)

```bash
# Build the image
docker build -t neo4j-graphbot .

# Run with config file
docker run -it --rm \
  --network host \
  -v $(pwd)/config.env:/app/config.env:ro \
  neo4j-graphbot
```

## Configuration File Format

The `config.env` file supports:

- **Comments**: Lines starting with `#` are ignored
- **Empty values**: Variables can be left empty to use defaults
- **Environment variables**: Standard `KEY=value` format

### Required Settings

- `NEO4J_PASSWORD` - Your Neo4j password (required)
- `GEMINI_API_KEY` - Your Gemini API key (required)

### Optional Settings (with defaults)

- `NEO4J_URI` - Default: `bolt://localhost:7687`
- `NEO4J_USER` - Default: `neo4j`
- `NEO4J_DATABASE` - Default: `neo4j` (or empty for default database)

## Connection Examples

### Local Neo4j (on your computer)

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mypassword
NEO4J_DATABASE=mydatabase
```

### Neo4j on Docker Host (from container)

```bash
NEO4J_URI=bolt://host.docker.internal:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mypassword
NEO4J_DATABASE=mydatabase
```

### Remote Neo4j Server

```bash
NEO4J_URI=bolt://neo4j.example.com:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mypassword
NEO4J_DATABASE=production_db
```

### Neo4j in Another Docker Container

```bash
NEO4J_URI=bolt://neo4j-container:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mypassword
NEO4J_DATABASE=mydatabase
```

## Using Docker Compose

### Basic Usage

```bash
# Start the service
docker-compose up

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down

# Rebuild after code changes
docker-compose up --build
```

## Security Notes

1. **Never commit `config.env` to git** - It contains sensitive credentials
2. The file is mounted as read-only (`:ro`) in the container
3. Use `.gitignore` to exclude `config.env` from version control

## Troubleshooting

### Cannot Connect to Neo4j

1. **Check your `NEO4J_URI` in `config.env`:**
   - Local: `bolt://localhost:7687`
   - Docker host: `bolt://host.docker.internal:7687`
   - Remote: `bolt://your-server:7687`

2. **Verify Neo4j is running:**
   ```bash
   # Check if Neo4j is accessible
   telnet localhost 7687
   ```

3. **Check firewall/ports:**
   - Ensure port 7687 is open
   - For remote connections, check firewall rules

### Configuration Not Loading

1. **Verify file path:**
   ```bash
   # Check if file exists
   ls -la config.env
   ```

2. **Check file permissions:**
   ```bash
   chmod 644 config.env
   ```

3. **Verify format:**
   - No spaces around `=`
   - One variable per line
   - No quotes needed (unless value contains spaces)

### API Key Issues

1. **Verify API key is set in `config.env`**
2. **Check API key format:**
   - Should start with `AIza`
   - Should be 39 characters long
3. **Get a new key:** https://makersuite.google.com/app/apikey

## Advanced Usage

### Multiple Configurations

Create different config files for different environments:

```bash
# Development
cp config.env config.dev.env
# Edit config.dev.env

# Production
cp config.env config.prod.env
# Edit config.prod.env

# Run with specific config
docker run -it --rm \
  --network host \
  -v $(pwd)/config.prod.env:/app/config.env:ro \
  neo4j-graphbot
```

### Using Environment Variables Instead

You can still override with environment variables:

```bash
docker run -it --rm \
  --network host \
  -e NEO4J_URI=bolt://custom-host:7687 \
  -e NEO4J_PASSWORD=custom_password \
  -v $(pwd)/config.env:/app/config.env:ro \
  neo4j-graphbot
```

Environment variables take precedence over `config.env`.

## Building for Different Platforms

```bash
# For ARM64 (Apple Silicon, Raspberry Pi)
docker build --platform linux/arm64 -t neo4j-graphbot .

# For AMD64 (Intel/AMD)
docker build --platform linux/amd64 -t neo4j-graphbot .
```

## Production Deployment

For production, consider:

1. **Use Docker secrets** instead of config file
2. **Add health checks** to docker-compose.yml
3. **Set resource limits**
4. **Use a reverse proxy** if exposing web interface

## Support

For issues or questions:
- Check the main [README.md](README.md)
- Review Docker logs: `docker-compose logs`
- Verify `config.env` format and values
