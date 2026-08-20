#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

CHECKPOINT="${RUN_DIR}/checkpoints/model.txt"

if [[ ! -f "${CHECKPOINT}" ]]; then
  echo "Missing ${CHECKPOINT}. Run the Train launcher first." >&2
  exit 1
fi

mkdir -p "${RUN_DIR}/metrics"

cat > "${RUN_DIR}/metrics/summary.txt" <<EOF
workflow=${RUN_KEY}
checkpoint=${CHECKPOINT}
evaluated_at=$(date --iso-8601=seconds)
EOF

echo "Wrote ${RUN_DIR}/metrics/summary.txt."

# Replace this placeholder with the real evaluation command, for example:
# python -u src/evaluate.py --checkpoint "${CHECKPOINT}" \
#   --output "${RUN_DIR}/metrics"
