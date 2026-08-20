#!/usr/bin/env bash
# 作业名称会出现在队列中，也会成为默认日志文件名的一部分。
#SBATCH --job-name=parameter-sweep
# 目标分区；使用 RTX 4070 时改为 epic-cluster-compute-rtx4070-01。
#SBATCH --partition=epic-cluster-compute-a100-01
# 运行 parameters.txt 的第 1 至 4 行，同时最多运行 2 个子任务。
#SBATCH --array=1-4%2
# 每个数组子任务只使用一个节点。
#SBATCH --nodes=1
# 每个数组子任务启动一个程序进程。
#SBATCH --ntasks=1
# 每个数组子任务申请的 CPU 核数；总并发 CPU 为本值乘以并发子任务数。
#SBATCH --cpus-per-task=2
# 每个数组子任务申报的预计内存；当前集群不会使用内存限制阻止任务运行。
#SBATCH --mem=4G
# 每个子任务需要完整 GPU 时，把本行开头改为单个 #。
##SBATCH --gres=gpu:1
# 每个子任务只需共享 GPU 时，把本行开头改为单个 #；不要同时启用 gpu 与 shard。
##SBATCH --gres=shard:1
# 若接受 CPU 超分，把本行开头改为单个 #；需要稳定 CPU 性能时保持原样。
##SBATCH --oversubscribe
# 每个数组子任务的最长运行时间，格式为 DD-HH:MM:SS 或 HH:MM:SS。
#SBATCH --time=04:00:00
# 标准输出日志；%x 是作业名称，%A 是数组主作业号，%a 是数组下标。
#SBATCH --output=%x-%A-%a.out
# 每个子任务的标准错误单独保存，避免日志互相覆盖。
#SBATCH --error=%x-%A-%a.err

set -euo pipefail
trap 'status=$?; echo "子任务在第 ${LINENO} 行失败，退出码 ${status}" >&2; exit "${status}"' ERR

WORK_DIR="${SLURM_SUBMIT_DIR}"
PARAMETER_FILE="${WORK_DIR}/parameters.txt"

cd "${WORK_DIR}"

if [[ ! -f "${PARAMETER_FILE}" ]]; then
  echo "找不到参数文件: ${PARAMETER_FILE}" >&2
  exit 1
fi

# Slurm 会自动设置 SLURM_ARRAY_TASK_ID 环境变量为当前子任务的数组下标。数组下标从 1 开始。
# 读取当前数组子任务对应的参数行。
PARAMETERS="$(sed -n "${SLURM_ARRAY_TASK_ID}p" "${PARAMETER_FILE}")"
if [[ -z "${PARAMETERS}" ]]; then
  echo "parameters.txt 没有第 ${SLURM_ARRAY_TASK_ID} 行，请同步修改 --array 范围。" >&2
  exit 1
fi

# 将当前行按空格拆成命令行参数。复杂参数可直接改写这里的读取逻辑。
read -r -a EXTRA_ARGS <<< "${PARAMETERS}"

echo "开始时间: $(date --iso-8601=seconds)"
echo "数组作业: ${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
echo "运行节点: ${SLURMD_NODENAME:-$(hostname)}"
echo "CPU 核数: ${SLURM_CPUS_PER_TASK}"
echo "可见 GPU: ${CUDA_VISIBLE_DEVICES:-未设置}"
echo "本次参数: ${PARAMETERS}"

# 按项目修改环境初始化。示例：
# source /workspace/envs/my-project/bin/activate

# 将下面命令替换为实际程序；当前参数行会原样传给程序。
echo "Scripts with parameters: ${EXTRA_ARGS[*]}"

echo "结束时间: $(date --iso-8601=seconds)"
