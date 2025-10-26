#!/bin/bash
# ===========================================
# NOVA VOICE - Conda Environment Setup
# ===========================================
# This script sets up the conda environment for Nova Voice backend services
# Run with: ./setup-conda.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

ENV_NAME="nova-voice"

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    print_error "Conda is not installed or not in PATH."
    print_info "Please install Miniconda or Anaconda first:"
    print_info "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

print_info "Setting up conda environment: ${ENV_NAME}"

# Check if environment already exists
if conda env list | grep -q "^${ENV_NAME} "; then
    print_warning "Environment '${ENV_NAME}' already exists."
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing existing environment..."
        conda env remove -n "${ENV_NAME}" -y
    else
        print_info "Using existing environment."
        print_success "Environment setup complete!"
        print_info "Activate with: conda activate ${ENV_NAME}"
        exit 0
    fi
fi

# Check if environment.yml exists
if [ ! -f "environment.yml" ]; then
    print_error "environment.yml not found in current directory."
    print_info "Please run this script from the backend/ directory."
    exit 1
fi

# Create environment
print_info "Creating conda environment from environment.yml..."
conda env create -f environment.yml

# Verify environment was created
if conda env list | grep -q "^${ENV_NAME} "; then
    print_success "Environment '${ENV_NAME}' created successfully!"

    # Activate and show info
    print_info "Activating environment..."
    CONDA_BASE=$(conda info --base)
    source "${CONDA_BASE}/etc/profile.d/conda.sh"
    conda activate "${ENV_NAME}"

    print_info "Environment info:"
    python --version
    pip --version

    print_success "Setup complete!"
    print_info ""
    print_info "Next steps:"
    print_info "1. Activate environment: conda activate ${ENV_NAME}"
    print_info "2. Run services: ./run-services.sh dev"
    print_info ""
    print_info "Or use the convenience script for everything:"
    print_info "  ./run-services.sh dev  # Will auto-activate conda environment"

else
    print_error "Failed to create environment '${ENV_NAME}'."
    exit 1
fi
