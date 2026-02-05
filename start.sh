#!/bin/bash

# QA Docker Test Manager - Startup Script
# This script starts the FastAPI server using uv

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}QA Docker Test Manager${NC}"
echo -e "${GREEN}========================${NC}\n"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo -e "Install uv with: ${YELLOW}curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo -e "Please start Docker Desktop or Docker daemon"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo -e "Creating .env file from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}Created .env file${NC}"
    fi
fi

# Sync dependencies
echo -e "${YELLOW}Syncing dependencies with uv...${NC}"
uv sync

# Get host and port from .env or use defaults
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

# Start the server
echo -e "\n${GREEN}Starting FastAPI server...${NC}"
echo -e "Host: ${YELLOW}${HOST}${NC}"
echo -e "Port: ${YELLOW}${PORT}${NC}"
echo -e "\n${GREEN}API Documentation:${NC}"
echo -e "  - Swagger UI: ${YELLOW}http://localhost:${PORT}/docs${NC}"
echo -e "  - ReDoc: ${YELLOW}http://localhost:${PORT}/redoc${NC}"
echo -e "  - Health Check: ${YELLOW}http://localhost:${PORT}/health${NC}"
echo -e "\n${GREEN}Press Ctrl+C to stop the server${NC}\n"

# Run the server with uv
uv run uvicorn app.main:app --host "${HOST}" --port "${PORT}" --reload
