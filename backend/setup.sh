#!/bin/bash

# BailBridge - Backend Setup Script
# Finalized for Phase 2 Production Readiness

echo ">>> Setting up BailBridge Backend..."

# 1. Create necessary directories
echo ">>> Creating folder structure..."
mkdir -p storage/evidence
mkdir -p knowledge_base

# 2. Install dependencies
echo ">>> Installing dependencies..."
pip install -r requirements.txt

# 3. Setup environment variables
if [ ! -f .env ]; then
    echo ">>> Creating .env from .env.example..."
    cp .env.example .env
    echo "!!! IMPORTANT: Please update the .env file with your API keys and Firebase credentials."
else
    echo ">>> .env file already exists."
fi

echo ">>> Setup Complete!"
echo ">>> Run 'python main.py' to start the server."
