#!/bin/bash

# EnergyPlus Dependencies Installation Script for WSL2 Ubuntu
# Run this script with: bash install_dependencies.sh

echo "=============================================="
echo "EnergyPlus Dependencies Installation"
echo "=============================================="
echo ""

# Check if running on Ubuntu
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "Detected OS: $NAME $VERSION"
else
    echo "Cannot detect OS. This script is for Ubuntu/Debian systems."
    exit 1
fi

echo ""
echo "This script will install the following packages:"
echo "  - libgomp1 (OpenMP runtime library - required)"
echo "  - libx11-6 (X11 client library - optional)"
echo "  - libxext6 (X11 extensions library - optional)"
echo "  - libgl1 (OpenGL library - optional)"
echo ""

read -p "Continue with installation? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Installation cancelled."
    exit 1
fi

echo ""
echo "Updating package lists..."
sudo apt-get update

echo ""
echo "Installing required dependencies..."
sudo apt-get install -y libgomp1

echo ""
echo "Installing optional dependencies..."
sudo apt-get install -y libx11-6 libxext6 libgl1 || echo "Some optional packages could not be installed (this is usually OK)"

echo ""
echo "=============================================="
echo "Testing EnergyPlus installation..."
echo "=============================================="

ENERGYPLUS_PATH="$HOME/EnergyPlus-23.2.0-7636e6b3e9-Linux-Ubuntu22.04-x86_64/energyplus"

if [ -f "$ENERGYPLUS_PATH" ]; then
    echo ""
    echo "Running: $ENERGYPLUS_PATH --version"
    $ENERGYPLUS_PATH --version

    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ SUCCESS! EnergyPlus is working correctly!"
        echo ""
        echo "Next steps:"
        echo "1. Install Python dependencies: pip install -r requirements.txt"
        echo "2. Download a weather file from: https://energyplus.net/weather"
        echo "3. Run the example: python examples/01_simple_box_simulation.py"
    else
        echo ""
        echo "❌ EnergyPlus test failed. There might be additional missing dependencies."
        echo "Try running: ldd $ENERGYPLUS_PATH"
        echo "to see which libraries are still missing."
    fi
else
    echo "❌ EnergyPlus executable not found at: $ENERGYPLUS_PATH"
    echo "Please check the installation path."
fi

echo ""
echo "=============================================="
echo "Installation complete!"
echo "=============================================="
