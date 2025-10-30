#!/bin/bash
# SafeLink Quick Start Script - Development Mode
# Run this script to start SafeLink in development

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/Backend/SafeLink_Backend"
FRONTEND_DIR="$PROJECT_ROOT/Frontend"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SafeLink Development Startup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

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
    echo -e "${YELLOW}Please edit .env file with your configuration.${NC}"
fi

# Check if database exists
if [ ! -f "$BACKEND_DIR/data/safelink.db" ]; then
    echo -e "${YELLOW}Database not found. Initializing...${NC}"
    cd "$BACKEND_DIR"
    source venv/bin/activate
    python Scripts/setup_db.py
    echo -e "${GREEN}Database initialized.${NC}"
fi

# Check if frontend dependencies installed
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Frontend dependencies not found. Installing...${NC}"
    cd "$FRONTEND_DIR"
    npm install
    echo -e "${GREEN}Frontend dependencies installed.${NC}"
fi

echo -e "${GREEN}Starting SafeLink in DEVELOPMENT mode...${NC}"
echo ""

# Start backend in background (development mode: auto-reload, single worker)
echo -e "${YELLOW}Starting Backend (port 8000)...${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate
uvicorn api:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
echo -e "${GREEN}Backend started (PID: $BACKEND_PID)${NC}"

# Wait for backend to start
sleep 3

# Start frontend
echo -e "${YELLOW}Starting Frontend (port 5173)...${NC}"
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend started (PID: $FRONTEND_PID)${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SafeLink Development Environment Ready!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Backend API:     ${GREEN}http://localhost:8000${NC}"
echo -e "API Docs:        ${GREEN}http://localhost:8000/docs${NC}"
echo -e "Frontend:        ${GREEN}http://localhost:5173${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for Ctrl+C
trap "echo -e '\n${YELLOW}Stopping services...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

# Keep script running
wait
