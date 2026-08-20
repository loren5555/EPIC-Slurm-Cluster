#!/usr/bin/env bash

set -euo pipefail

: "${OOD_PROJECT_DIR:?This script must run from an OOD Project Manager project.}"

RUN_KEY="${OOD_WORKFLOW_SYNC_KEY:-manual-${SLURM_JOB_ID:-local}}"
RUN_DIR="${OOD_PROJECT_DIR}/outputs/${RUN_KEY}"

export RUN_KEY RUN_DIR
