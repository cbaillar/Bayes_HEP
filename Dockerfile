# ─────────────────────────────────────────────
# Base image: Rivet + Pythia8 (pinned version for reproducibility)
# ─────────────────────────────────────────────
FROM hepstore/rivet-pythia:4.1.0

# ─────────────────────────────────────────────
# System configuration
# ─────────────────────────────────────────────

# Suppress interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# Use bash for all subsequent RUN commands
SHELL ["/bin/bash", "-c"]

# ─────────────────────────────────────────────
# System dependencies
# ─────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    python3-venv \
    git \
    wget \
    cmake \
    build-essential \
    vim \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────
# Python dependencies
# ─────────────────────────────────────────────
# bilby       — Bayesian inference / sampler framework
# surmise     — GP emulation
# scikit-learn — GP emulation (scikit backend) and scalers
# ultranest   — nested sampling sampler
# ipykernel / jupyter — notebook support
# seaborn     — posterior correlation heatmaps
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        bilby \
        surmise \
        scikit-learn \
        ultranest \
        dill \
        ipykernel \
        jupyter \
        seaborn

# ─────────────────────────────────────────────
# Bayes_HEP package
# ─────────────────────────────────────────────

# Install package source into the shared directory
COPY Bayes_HEP /usr/local/share/Bayes_HEP

# Ensure __init__.py files exist so Python treats subdirs as packages
RUN touch /usr/local/share/Bayes_HEP/__init__.py && \
    touch /usr/local/share/Bayes_HEP/Design_Points/__init__.py && \
    touch /usr/local/share/Bayes_HEP/Emulation/__init__.py && \
    touch /usr/local/share/Bayes_HEP/Calibration/__init__.py

# Allow all users to read/write/execute (needed in shared HPC environments)
RUN chmod -R a+rwX /usr/local/share/Bayes_HEP

# ─────────────────────────────────────────────
# Environment
# ─────────────────────────────────────────────

# Make Bayes_HEP importable from anywhere without installing via pip
ENV PYTHONPATH="/usr/local/lib/python3.10/site-packages:/usr/local/share"

# Clear PYTHIA8DATA so Pythia uses the version bundled in the base image
ENV PYTHIA8DATA=

# ─────────────────────────────────────────────
# Working directory and entrypoint
# ─────────────────────────────────────────────

# /workdir is bind-mounted at runtime (e.g. -v "$PWD":/workdir)
# COPY . /workdir  ← uncomment to bake a project into the image instead
WORKDIR /workdir

CMD ["/bin/bash"]
