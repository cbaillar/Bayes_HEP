# Start from a specific tested version
FROM hepstore/rivet-pythia:latest

# Set environment to non-interactive
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    python3-venv \
    git \
    wget \
    cmake \
    build-essential \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set default shell to bash
SHELL ["/bin/bash", "-c"]

# Upgrade pip and install Python packages
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir bilby surmise scikit-learn

# Create working directory
WORKDIR /workdir

# Default command
CMD ["/bin/bash"]