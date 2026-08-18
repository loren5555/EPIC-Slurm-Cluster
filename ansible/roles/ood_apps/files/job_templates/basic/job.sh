#!/usr/bin/env bash
#SBATCH --job-name=basic
#SBATCH --partition=epic-cluster-compute-a100-01
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --output=%x-%j.out

set -euo pipefail

hostname
