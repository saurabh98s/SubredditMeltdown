#!/bin/bash
set -e

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "===== Setting up Reddit Meltdown Analysis project ====="

# Create data directories
echo "Creating data directories..."
mkdir -p data/raw
mkdir -p data/processed
mkdir -p data/analytics/sentiment
mkdir -p data/analytics/keywords
mkdir -p data/analytics/events_correlation

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs

# Copy events data file to the right location
if [ -f "data/events.csv" ]; then
    echo "Events file already exists."
else
    echo "Creating sample events file..."
    cp "${PROJECT_ROOT}/data/events.csv" "${PROJECT_ROOT}/data/"
fi

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists."
else
    echo "Creating new virtual environment..."
    python -m venv venv
    
    # Activate virtual environment
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    # Install dependencies
    echo "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Set up frontend environment
echo "Setting up frontend environment..."
if [ -d "frontend/node_modules" ]; then
    echo "Frontend dependencies already installed."
else
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo "Setup completed successfully!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate  # On Linux/Mac"
echo "  source venv/Scripts/activate  # On Windows (Git Bash)"
echo ""
echo "To start the Docker environment, run:"
echo "  docker-compose up -d"
echo ""
echo "To run the data processing pipeline, run:"
echo "  infra/run_pipeline.sh" 