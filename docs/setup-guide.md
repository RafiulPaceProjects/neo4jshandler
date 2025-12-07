# Setup Guide

This guide details how to set up the **Neo4j GraphBot** for local development.

## Prerequisites

*   **Python 3.8+**
*   **Neo4j Database** (Local instance or AuraDB)
*   **API Key** for your LLM Provider (e.g., Google Gemini, OpenAI)

## Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/neo4j-graphbot.git
    cd neo4j-graphbot
    ```

2.  **Create a Virtual Environment**
    It is recommended to use a virtual environment to manage dependencies.
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -e .[dev]
    ```

## Configuration

The application requires configuration for both the database connection and the LLM provider.

### 1. Environment Variables (`.env`)
Create a `.env` file in the `neo4jsinteract/config` directory (or root) based on the template.

```bash
cp config/config.env.template config/config.env
```

Edit `config/config.env` with your credentials:

```ini
# Neo4j Settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# LLM Settings (Google Gemini Example)
GOOGLE_API_KEY=your_api_key_here
```

### 2. Provider Configuration (`providers.yaml`)
The `config/providers.yaml` file defines the model behavior and prompts.

```yaml
provider: "gemini"  # or "openai"
models:
  main: "gemini-1.5-pro"
  worker: "gemini-1.5-flash"
...
```

## Running the Application

### CLI Mode
To start the interactive CLI:

```bash
graphbot
```

### Control Panel
To launch the configuration control panel:

```bash
python scripts/control_panel.py
```

## Docker Setup

If you prefer to run using Docker:

1.  **Build the Image**
    ```bash
    docker build -t neo4j-graphbot .
    ```

2.  **Run Container**
    ```bash
    docker run -it --env-file config/config.env neo4j-graphbot
    ```

## Troubleshooting

*   **Connection Refused**: Ensure your Neo4j database is running and the `NEO4J_URI` is reachable.
*   **Auth Error**: Double-check `NEO4J_USERNAME` and `NEO4J_PASSWORD`.
*   **API Key Error**: Verify your LLM provider API key is set in `.env`.

