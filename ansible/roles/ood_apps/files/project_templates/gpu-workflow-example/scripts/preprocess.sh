#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

DATASET="${DATASET:-example-dataset}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-baseline}"

mkdir -p "${RUN_DIR}/inputs"

cat > "${RUN_DIR}/inputs/metadata.txt" <<EOF
dataset=${DATASET}
experiment=${EXPERIMENT_NAME}
prepared_at=$(date --iso-8601=seconds)
EOF

echo "Prepared ${DATASET} for workflow ${RUN_KEY}."

# Replace this placeholder with the real preprocessing command, for example:
# python -u src/preprocess.py --dataset "${DATASET}" --output "${RUN_DIR}/inputs"
