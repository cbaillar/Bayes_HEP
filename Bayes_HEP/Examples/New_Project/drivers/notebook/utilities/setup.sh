#!/bin/bash
# setup.sh — Run once to configure environment for Bayes_HEP

# === Parameters ===
USERNAME=$1
USER_DIR="/lustre/isaac24/proj/UTK0244/${USERNAME}"
CONTAINER="${USER_DIR}/Bayes_HEP/bayes_hep.sif"
BIND_PATH="${USER_DIR}/Bayes_HEP:/workdir"
KERNEL_NAME="bayes_hep"
DISPLAY_NAME="Bayes HEP (Apptainer)"

# === Add module load to .bashrc ===
if ! grep -q "module load anaconda3/2024.06" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# Bayes_HEP" >> ~/.bashrc
    echo "module load anaconda3/2024.06" >> ~/.bashrc
    echo "✅ Added anaconda3/2024.06 to ~/.bashrc"
else
    echo "⏭️  anaconda3/2024.06 already in ~/.bashrc — skipping"
fi

# === Load anaconda for this session ===
module load anaconda3/2024.06

# === Install kernel ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/install_kernel.sh" "$CONTAINER" "$BIND_PATH" "$KERNEL_NAME" "$DISPLAY_NAME"

echo ""
echo "✅ Setup complete. Start Jupyter with:"
echo "   jupyter notebook --no-browser --port=8888 --ip=0.0.0.0"