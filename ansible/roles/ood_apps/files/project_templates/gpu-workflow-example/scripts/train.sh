#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

EXPERIMENT_NAME="${EXPERIMENT_NAME:-baseline}"
INPUT_METADATA="${RUN_DIR}/inputs/metadata.txt"

if [[ ! -f "${INPUT_METADATA}" ]]; then
  echo "Missing ${INPUT_METADATA}. Run the Preprocess launcher first." >&2
  exit 1
fi

mkdir -p "${RUN_DIR}/checkpoints"

echo "Training experiment ${EXPERIMENT_NAME} for workflow ${RUN_KEY}."
echo "Node: ${SLURMD_NODENAME:-$(hostname)}"
echo "Visible GPU: ${CUDA_VISIBLE_DEVICES:-none}"
nvidia-smi -L || true

printf 'placeholder checkpoint for %s\n' "${EXPERIMENT_NAME}" \
  > "${RUN_DIR}/checkpoints/model.txt"

# Replace the placeholder above with the real training command, for example:
# python -u src/train.py --input "${RUN_DIR}/inputs" \
#   --output "${RUN_DIR}/checkpoints" --experiment "${EXPERIMENT_NAME}"
