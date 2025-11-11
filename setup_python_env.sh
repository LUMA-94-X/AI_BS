#!/bin/bash

# Python Environment Setup Script
# Run this script with: bash setup_python_env.sh

echo "=============================================="
echo "Python Environment Setup"
echo "=============================================="
echo ""

# Get project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "Project directory: $PROJECT_DIR"
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version)
echo "Found: $PYTHON_VERSION"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    exit 1
fi

# Check if python3-venv is installed
echo ""
echo "Checking for python3-venv..."
if ! dpkg -l | grep -q python3.*-venv; then
    echo "⚠️  python3-venv is not installed."
    echo ""
    echo "Installing python3-venv..."
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-pip

    if [ $? -ne 0 ]; then
        echo "❌ Failed to install python3-venv"
        exit 1
    fi
else
    echo "✅ python3-venv is already installed"
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists at: venv"
    read -p "Remove and recreate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
    else
        echo "Keeping existing virtual environment."
    fi
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo "✅ Virtual environment created successfully!"
    else
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing Python dependencies from requirements.txt..."
echo "This may take a few minutes..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All Python dependencies installed successfully!"
else
    echo ""
    echo "⚠️  Some dependencies failed to install. Check the error messages above."
fi

# Verify key packages
echo ""
echo "Verifying key packages..."
python3 -c "import eppy; print('✅ eppy:', eppy.__version__)" 2>/dev/null || echo "❌ eppy not installed"
python3 -c "import pandas; print('✅ pandas:', pandas.__version__)" 2>/dev/null || echo "❌ pandas not installed"
python3 -c "import pydantic; print('✅ pydantic:', pydantic.__version__)" 2>/dev/null || echo "❌ pydantic not installed"

echo ""
echo "=============================================="
echo "Setup Complete!"
echo "=============================================="
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the first example:"
echo "  source venv/bin/activate"
echo "  python examples/01_simple_box_simulation.py"
echo ""
echo "Note: You will need a weather file (.epw) for full simulations."
echo "Download from: https://energyplus.net/weather"
echo ""
