#!/usr/bin/env bash
#SBATCH --job-name=gpu
#SBATCH --partition=epic-cluster-compute-a100-01
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --time=08:00:00
#SBATCH --output=%x-%j.out

set -euo pipefail

nvidia-smi -L
