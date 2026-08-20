#!/usr/bin/env bash
#SBATCH --output=output/%x-%j.out


set -euo pipefail

RUN_KEY="${OOD_WORKFLOW_SYNC_KEY:-manual-${SLURM_JOB_ID:-local}}"

echo "${RUN_KEY}"
