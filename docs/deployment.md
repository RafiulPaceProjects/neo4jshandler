# Deployment Guide

This guide covers how to build and deploy the Neo4j GraphBot for production use.

## Build from Source

To build a distributable Python package (wheel):

1.  **Clean previous builds**
    ```bash
    rm -rf dist/ build/ *.egg-info
    ```

2.  **Build Package**
    ```bash
    python -m build
    ```
    This will create a `.whl` file in the `dist/` directory.

3.  **Install**
    You can install this wheel in any environment:
    ```bash
    pip install dist/neo4j_graphbot-1.0.0-py3-none-any.whl
    ```

## Docker Deployment

For containerized environments (Kubernetes, ECS, or simple Docker Compose).

### 1. Structure
Ensure your `Dockerfile` and `docker-compose.yml` are present in the root.

### 2. Build Image
```bash
docker build -t neo4j-graphbot:latest .
```

### 3. Run with Environment Variables
It is best practice to inject credentials via environment variables rather than baking them into the image.

```bash
docker run -it \
  -e NEO4J_URI="bolt://your-prod-db:7687" \
  -e NEO4J_USERNAME="neo4j" \
  -e NEO4J_PASSWORD="prod_password" \
  -e GOOGLE_API_KEY="prod_api_key" \
  neo4j-graphbot:latest
```

### 4. Docker Compose
For a full stack (if hosting Neo4j alongside):

```yaml
version: '3.8'
services:
  graphbot:
    build: .
    environment:
      - NEO4J_URI=bolt://neo4j:7687
    depends_on:
      - neo4j
  
  neo4j:
    image: neo4j:5.15.0
    environment:
      - NEO4J_AUTH=neo4j/password
    ports:
      - "7687:7687"
      - "7474:7474"
```

## CI/CD Pipeline Recommendations

*   **Linting**: Run `flake8` or `pylint` on every commit.
*   **Testing**: Run `pytest tests/` to ensure regression testing.
*   **Security**: Scan image for vulnerabilities using `trivy` or similar tools before pushing to registry.

