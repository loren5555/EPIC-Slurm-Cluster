#!/usr/bin/env bash
#SBATCH --job-name=array
#SBATCH --partition=epic-cluster-compute-a100-01
#SBATCH --array=1-10%2
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=04:00:00
#SBATCH --output=%x-%A-%a.out

set -euo pipefail

echo "array index: ${SLURM_ARRAY_TASK_ID}"
