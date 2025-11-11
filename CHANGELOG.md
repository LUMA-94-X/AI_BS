# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-10

### Added
- Initial project setup and structure
- Configuration management system with YAML support
- Simple box geometry generator for basic building models
- Material and construction definitions
- EnergyPlus simulation runner with single and batch execution
- Parallel simulation processing with progress tracking
- Example scripts for simple and batch simulations
- Comprehensive documentation (README, ARCHITECTURE, GETTING_STARTED)
- Unit tests for geometry and configuration modules
- Python package configuration (pyproject.toml)

### Features
- **Geometry Generation**
  - Simple box-shaped buildings with configurable parameters
  - Multi-floor support
  - Automatic window generation based on window-to-wall ratio
  - Orientation control

- **Simulation**
  - Single simulation execution
  - Batch processing with parallel execution
  - Error handling and validation
  - Progress tracking with tqdm
  - Timeout protection

- **Configuration**
  - YAML-based configuration with Pydantic validation
  - Auto-detection of EnergyPlus installation
  - Flexible simulation parameters

- **Materials & Constructions**
  - Basic material library (concrete, insulation, brick, etc.)
  - Standard constructions for walls, roofs, floors
  - Simple double glazing windows

### Documentation
- Main README with installation and usage instructions
- Architecture documentation with system design
- Getting Started guide for new users
- Example scripts with detailed comments
- Unit tests with pytest

### Dependencies
- eppy >= 0.5.63
- geomeppy >= 0.11.8
- pandas >= 2.0.0
- pydantic >= 2.0.0
- tqdm >= 4.65.0
- pytest >= 7.0.0 (dev)

## [Unreleased]

### Planned
- Post-processing module for result analysis
- Enhanced geometry generators (L-shape, U-shape, complex forms)
- IFC and gbXML import capabilities
- TABULA building database integration
- Detailed HVAC system templates
- Co-simulation support (FMI/FMU)
- Hardware-in-the-Loop interfaces
- Machine Learning integration for surrogate models
- Web-based GUI
- Optimization algorithms
- Real-time simulation capabilities
