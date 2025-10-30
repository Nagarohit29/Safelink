#!/bin/bash
# SafeLink Quick Start Script - Production Mode
# Run this script to start SafeLink in production

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/Backend/SafeLink_Backend"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SafeLink Production Startup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root (required for packet capture)
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (sudo)${NC}" 
   echo "Packet capture requires elevated privileges."
   exit 1
fi

# Check if virtual environment exists
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    cd "$BACKEND_DIR"
    python3.11 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${GREEN}Virtual environment created successfully.${NC}"
else
    echo -e "${GREEN}Virtual environment found.${NC}"
fi

# Check if .env file exists
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "${YELLOW}Warning: .env file not found!${NC}"
    echo "Copying .env.example to .env..."
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo -e "${RED}IMPORTANT: Edit .env file with your configuration before running!${NC}"
    echo "Especially: SECRET_KEY, NETWORK_INTERFACE"
    exit 1
fi

# Check if database exists
if [ ! -f "$BACKEND_DIR/data/safelink.db" ]; then
    echo -e "${YELLOW}Database not found. Initializing...${NC}"
    cd "$BACKEND_DIR"
    source venv/bin/activate
    python Scripts/setup_db.py
    echo -e "${GREEN}Database initialized.${NC}"
fi

# Start backend
echo -e "${GREEN}Starting SafeLink backend...${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate

# Production mode: 4 workers, no reload
uvicorn api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --access-log

echo -e "${GREEN}SafeLink backend started successfully!${NC}"
echo -e "Access the API at: ${GREEN}http://localhost:8000${NC}"
echo -e "API Documentation: ${GREEN}http://localhost:8000/docs${NC}"
