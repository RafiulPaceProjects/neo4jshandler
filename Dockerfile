FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ /app/src/

# Copy configuration template
COPY config/config.env.template /app/config/config.env.template

# Copy requirements
COPY requirements.txt pyproject.toml setup.py /app/

# Create a non-root user for security
RUN useradd -m -u 1000 graphbot && \
    chown -R graphbot:graphbot /app

# Switch to non-root user
USER graphbot

# Add user local bin to PATH so 'graphbot' command is found
ENV PATH="/home/graphbot/.local/bin:${PATH}"

# Set environment variables with defaults
ENV PYTHONUNBUFFERED=1
ENV CONFIG_FILE=/app/config/config.env
ENV PYTHONPATH=/app/src

# Install the package in user mode
RUN pip install --user --no-cache-dir -e .

# Entry point script that loads config
ENTRYPOINT ["/bin/sh", "-c", "if [ -f /app/config/config.env ]; then export $(cat /app/config/config.env | grep -v '^#' | xargs); fi && graphbot"]

