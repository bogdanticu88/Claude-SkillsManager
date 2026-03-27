#!/bin/bash
# SkillPM Registry - Run Script
# Author: Bogdan Ticu
# License: MIT
#
# Start the registry API server locally for development.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Create virtualenv if needed
if [ ! -d "venv" ]; then
    echo "Creating virtualenv..."
    python3 -m venv venv
fi

# Activate and install deps
source venv/bin/activate
pip install -q -r registry/requirements.txt

# Seed data if requested
if [ "$1" = "--seed" ]; then
    echo "Seeding database..."
    python3 registry/seed.py
fi

# Run the server
echo "Starting SkillPM Registry on http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo "Frontend: http://localhost:8000/app"
uvicorn registry.main:app --host 0.0.0.0 --port 8000 --reload
