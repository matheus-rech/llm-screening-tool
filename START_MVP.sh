#!/bin/bash

echo "🚀 INICIANDO MVP DO SCREENING CENTER"
echo "=================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Set environment variables
export FLASK_ENV=development
export OPENAI_API_KEY=${OPENAI_API_KEY:-"CHANGE_ME"}
export ENTREZ_EMAIL=${ENTREZ_EMAIL:-"your-email@domain.com"}

echo ""
echo "🔥 STARTING SCREENING CENTER MVP"
echo "=================================="
echo "Access: http://localhost:8080"
echo "Press CTRL+C to stop"
echo ""

# Run the application
python run.py