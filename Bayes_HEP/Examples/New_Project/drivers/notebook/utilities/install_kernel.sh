#!/bin/bash

CONTAINER=$1
BIND_PATH=$2
KERNEL_NAME=${3:-bayes_hep}
DISPLAY_NAME=${4:-"Bayes HEP (Apptainer)"}

apptainer exec --bind "$BIND_PATH" "$CONTAINER" \
    python3 -m ipykernel install --user --name="$KERNEL_NAME" --display-name="$DISPLAY_NAME"

cat > ~/.local/share/jupyter/kernels/${KERNEL_NAME}/kernel.json << EOF
{
 "argv": [
  "apptainer", "exec",
  "--bind", "${BIND_PATH}",
  "${CONTAINER}",
  "python3", "-m", "ipykernel_launcher", "-f", "{connection_file}"
 ],
 "display_name": "${DISPLAY_NAME}",
 "language": "python"
}
EOF

echo "Kernel '${DISPLAY_NAME}' installed and patched."