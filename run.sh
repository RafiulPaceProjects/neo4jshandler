#!/bin/bash
# Convenience script to run GraphBot with Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   ${RED}Neo4j GraphBot - Docker Runner${BLUE}   ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
echo ""

# Check if config.env file exists
if [ ! -f config/config.env ]; then
    echo -e "${YELLOW}⚠️  config.env file not found!${NC}"
    if [ -f config/config.env.template ]; then
        echo -e "${YELLOW}Creating config.env from template...${NC}"
        cp config/config.env.template config/config.env
        echo -e "${GREEN}✓ Created config/config.env file${NC}"
        echo -e "${YELLOW}Please edit config/config.env with your configuration before running again.${NC}"
        echo -e "${BLUE}   Edit: nano config/config.env${NC}"
        exit 1
    else
        echo -e "${RED}✗ config/config.env.template not found!${NC}"
        echo -e "${YELLOW}Creating a basic config.env file...${NC}"
        mkdir -p config
        cat > config/config.env << 'EOF'
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
NEO4J_DATABASE=

# Gemini API
GEMINI_API_KEY=your_api_key_here
MAIN_MODEL=gemini-3-pro-preview
WORKER_MODEL=gemini-1.5-flash
EOF
        echo -e "${GREEN}✓ Created config/config.env file${NC}"
        echo -e "${YELLOW}Please edit config/config.env with your configuration before running again.${NC}"
        exit 1
    fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running!${NC}"
    echo -e "${YELLOW}Please start Docker and try again.${NC}"
    exit 1
fi

# Check if image exists, build if not
if ! docker images | grep -q neo4j-graphbot; then
    echo -e "${BLUE}📦 Building Docker image...${NC}"
    docker build -t neo4j-graphbot .
    echo -e "${GREEN}✓ Image built successfully${NC}"
fi

# Validate config file
if ! grep -q "NEO4J_PASSWORD=" config/config.env || grep -q "NEO4J_PASSWORD=your_password_here" config/config.env || grep -q "NEO4J_PASSWORD=$" config/config.env; then
    echo -e "${RED}✗ NEO4J_PASSWORD not set in config/config.env${NC}"
    echo -e "${YELLOW}Please edit config/config.env and set your Neo4j password.${NC}"
    exit 1
fi

if ! grep -q "GEMINI_API_KEY=" config/config.env || grep -q "GEMINI_API_KEY=your_api_key_here" config/config.env || grep -q "GEMINI_API_KEY=$" config/config.env; then
    echo -e "${RED}✗ GEMINI_API_KEY not set in config/config.env${NC}"
    echo -e "${YELLOW}Please edit config/config.env and set your Gemini API key.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Configuration file validated${NC}"
echo -e "${BLUE}🚀 Starting GraphBot...${NC}"
echo ""

# Run the container with config file mounted
docker run -it --rm \
    --network host \
    -v "$(pwd)/config/config.env:/app/config/config.env:ro" \
    neo4j-graphbot

