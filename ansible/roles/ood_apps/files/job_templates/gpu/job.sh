#!/usr/bin/env bash
# 作业名称会出现在队列中，也会成为默认日志文件名的一部分。
#SBATCH --job-name=gpu-train
# 目标分区；使用 RTX 4070 时改为 epic-cluster-compute-rtx4070-01。
#SBATCH --partition=epic-cluster-compute-a100-01
# GPU 作业通常只需要一个节点。
#SBATCH --nodes=1
# 单进程训练使用一个 task；多进程训练请按程序启动方式调整。
#SBATCH --ntasks=1
# 为当前 task 分配的 CPU 核数，用于数据加载和预处理。
#SBATCH --cpus-per-task=8
# 申报预计内存用量；当前集群不会使用内存限制阻止任务运行。
#SBATCH --mem=32G
# 默认申请一张完整 GPU；多卡训练可改为 gpu:2 等。
#SBATCH --gres=gpu:1
# 小任务若只需共享 GPU：注释上一条 gpu:1，并把本行开头改为单个 #。
##SBATCH --gres=shard:1
# 若接受 CPU 超分，把本行开头改为单个 #；需要稳定 CPU 性能时保持原样。
##SBATCH --oversubscribe
# 最长运行时间，格式为 DD-HH:MM:SS 或 HH:MM:SS。
#SBATCH --time=08:00:00
# 标准输出日志；%x 是作业名，%j 是作业号。
#SBATCH --output=%x-%j.out
# 标准错误单独保存，便于快速定位失败原因。
#SBATCH --error=%x-%j.err

set -euo pipefail
trap 'status=$?; echo "作业在第 ${LINENO} 行失败，退出码 ${status}" >&2; exit "${status}"' ERR

# 默认从提交目录运行。也可以改成固定实验目录，例如：
# WORK_DIR=/workspace/runs/<group>/<user>/<experiment>
WORK_DIR="${SLURM_SUBMIT_DIR}"
cd "${WORK_DIR}"

mkdir -p checkpoints

echo "开始时间: $(date --iso-8601=seconds)"
echo "作业编号: ${SLURM_JOB_ID}"
echo "运行节点: ${SLURMD_NODENAME:-$(hostname)}"
echo "工作目录: ${PWD}"
echo "CPU 核数: ${SLURM_CPUS_PER_TASK}"
echo "可见 GPU: ${CUDA_VISIBLE_DEVICES:-未设置}"

# 按项目修改环境初始化。示例：
# source /workspace/envs/my-project/bin/activate
# module load cuda

# 将下面命令替换为实际程序。使用 srun 可继承 Slurm 分配的 CPU/GPU 资源。
nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv

echo "结束时间: $(date --iso-8601=seconds)"
