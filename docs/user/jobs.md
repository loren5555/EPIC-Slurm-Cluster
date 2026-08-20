---
layout: default
title: 提交任务
parent: 用户文档
nav_order: 2
---

# 提交任务

EPIC 有两种任务入口：Interactive Apps 适合调试和交互式工作；Job Composer 适合训练、批处理和需要运行较长时间的任务。

## 先选择合适的入口


| 任务类型             | 推荐入口                   | 适合做什么                       |
| ---------------------- | ---------------------------- | ---------------------------------- |
| 调试、查看环境       | Interactive Apps           | 交互式开发，最长 32 小时         |
| 训练或推理           | Job Composer 的 GPU 模板   | 需要显式申请 GPU 的任务          |
| 同一程序运行多个参数 | Job Composer 的 Array 模板 | 参数扫描、批量评测和独立样本任务 |
| 已经有自己的作业脚本 | Script App 或 Job Composer | 直接提交已有的 Slurm 脚本        |

重负载训练不要长期占用 Interactive App。需要 GPU 时需在 Slurm 作业中申请。

## 使用 Job Composer 提交任务

### 1. 打开 Job Composer

1. 登录 OOD。
2. 打开 **Job Composer**。
3. 点击 **New Job**，选择 **From Template**。
4. 选择 `GPU Slurm job` 或 `Slurm array job`。
5. 设置任务名称，点击**Create New Job**。

**Composer**创建的是一份可编辑的作业目录，不会立即提交任务。创建后先检查脚本，再点击提交。注意Job的目录大小<span style="color:red">不能超过65kb</span>.

### 2. 作业目录

一个模板任务通常包含：

```text
Job/
├── manifest.yml   # Job Composer 的名称和元数据
└── job.sh         # 真正提交给 Slurm 的脚本
```

如果程序依赖多个脚本或配置文件，可以把它们放进同一个任务目录。程序代码和大型数据不要复制到 Job Composer 目录中，脚本应通过绝对路径或工作目录访问 `/workspace`、`/data` 中的内容。

### 3. 编辑 `job.sh`

打开任务后，在 Job Composer 的编辑区域选择 `job.sh`。至少检查以下内容：

- `--partition`：填写你有权限使用的完整主机名分区；
- `--cpus-per-task`：填写程序实际需要的 CPU 核数；
- `--mem`：填写任务需要的内存，例如 `32G`；
- `--time`：填写合理的最长运行时间；
- `--gres=gpu:N`：GPU 任务填写申请数量，CPU 任务删除这一行；
- `--output`：确认日志文件名不会被多个任务覆盖；
- 脚本最后的命令：替换模板中的示例命令。

分区名称必须是完整计算主机名，例如：

```bash
# A100 host partition
#SBATCH --partition=epic-cluster-compute-a100-01

# RTX 4070 host partition
#SBATCH --partition=epic-cluster-compute-rtx4070-01
```

### 4. 选择工作目录并准备日志目录

作业脚本中的 `cd` 决定程序从哪里运行。建议每次实验使用独立目录：

```bash
set -euo pipefail

cd /workspace/runs/<group>/<user>/<run-name>
mkdir -p logs
python train.py
```

注意脚本会被复制到<span style="color:red">计算节点</span>运行。所有路径都是计算节点路径。
如果 `cd` 的目录不存在，作业会在正式运行前失败。可以在脚本中先创建目录，或者在提交前通过 OOD 控制节点终端、SSH 或 VS Code Remote-SSH 创建目录。

## 内置模板

### GPU：单卡或多卡任务

GPU 模板默认申请一张 GPU。根据程序需求修改 `--gres`，并在脚本中启动训练程序：

```bash
#!/usr/bin/env bash
#SBATCH --job-name=training
#SBATCH --partition=epic-cluster-compute-a100-01
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --time=08:00:00
#SBATCH --output=%x-%j.out

set -euo pipefail
cd /workspace/runs/<group>/<user>/<run-name>

echo "host: $(hostname)"
echo "job: ${SLURM_JOB_ID}"
nvidia-smi -L
python train.py --output-dir checkpoints
```

申请两张卡时使用 `--gres=gpu:2`。

### Array：批量运行多个任务

Array 模板使用 `SLURM_ARRAY_TASK_ID` 区分不同子任务，可以通过这个变量控制多个任务之间的变量。下面的 `1-10%2` 表示创建 10 个子任务，同时最多运行 2 个：

```bash
#!/usr/bin/env bash
#SBATCH --job-name=evaluate
#SBATCH --partition=epic-cluster-compute-a100-01
#SBATCH --array=1-10%2
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=04:00:00
#SBATCH --output=logs/%x-%A-%a.out

set -euo pipefail
mkdir -p logs
cd /workspace/runs/<group>/<user>/<run-name>

echo "array index: ${SLURM_ARRAY_TASK_ID}"
python evaluate.py --index "${SLURM_ARRAY_TASK_ID}"
```

数组任务的作业号通常包含主作业号和数组下标，例如 `12345_7`。查看、取消或查询数组任务时，可以使用主作业号，也可以指定某一个子任务。注意 "cpus-per-task" 描述的是<span style="color:red">为每个子任务</span>分配的CPU核数。实际申请数量 = 子任务并行数量 * cpus-per-task，不要超额申请导致永久排队。例如模板中并行2个任务，每个任务2个CPU核心，实际上会申请4个CPU核心。

## 使用 Project Manager 管理项目

如果你需要反复运行一组脚本、保存输入输出文件，或把多个 Slurm 作业串成一个流程，可以使用 OOD 4.2 的 **Project Manager**。它比单独创建 Job Composer 任务更适合长期项目：项目目录保存脚本、输入数据和输出结果，项目中的 Launcher 负责提交作业，Workflow 负责组织作业依赖。

### 1. 创建项目并上传文件

1. 登录 OOD，打开 **Project Manager**。
2. 点击右上角 **Create a new project**。
3. 填写项目名称，可选择一个图标，然后点击 **Save**。
4. 点击项目名称进入项目面板。
5. 点击项目目录下的 **Open in files app**，在 OOD 文件管理器中上传脚本、配置文件和小型输入文件。

项目目录可以按自己的习惯组织，例如：

```text
my-project/
├── scripts/
│   ├── preprocess.sh
│   └── train.sh
├── configs/
└── outputs/
```

需要被其他脚本直接调用的文件应具有执行权限。主脚本不一定要有执行权限，因为它会由 Slurm 脚本提交；但被主脚本直接调用的辅助脚本必须可执行。在 OOD 文件管理器中可以修改权限，也可以在控制节点终端运行：

```bash
chmod u+x ~/projects/my-project/scripts/*.sh
```

注意虽然程序运行在计算节点，但是代码是存储在控制节点的。注意控制节点的5Gb存储限额。

### 2. 从示例模板创建项目

集群提供 **GPU Workflow Example** 模板，包含预处理、训练和评测脚本，用于
演示 Project Manager 的 Launcher、Workflow、GPU 资源申请和
`OOD_WORKFLOW_SYNC_KEY` 输出隔离。

1. 在 Project Manager 首页点击 **Create a new project**。
2. 选择 **GPU Workflow Example**，填写新项目名称后保存。
3. OOD 会为你创建可写的私有副本；打开项目中的 `README.md` 和 `scripts/`，
   再按自己的实验修改代码和配置。

模板由系统维护，你的项目副本才是创建 Launcher、修改脚本、保存配置和输出的
位置。

示例项目的推荐 Workflow 为：

```text
Preprocess  →  Train  →  Evaluate
```

其中只有 `Train` 通常需要 GPU；默认 Launcher 会包含 Account 与 Queue 下拉
字段。Queue 即目标计算分区，选择 A100 或 RTX 4070 主机对应的分区。每次
Workflow 运行的文件会写入 `outputs/<OOD_WORKFLOW_SYNC_KEY>/`，因此多个工作流
不会覆盖彼此的中间结果。

### 3. 创建 Launcher

Launcher 是“一个表单 + 一个脚本”。在项目面板左侧点击 **New Launcher**，填写名称并保存，然后点击 Launcher 卡片上的 **Edit** 编辑表单。

每个 Launcher 至少包含两个必需字段：

- `cluster`：选择集群，当前选择 `epic`；
- `script`：选择项目目录中的脚本。
- `Queue`: 选择提交的主机

前两个字段由 OOD 自动提供。`Queue`通过点击**Add new option**加入。保存 Launcher 后点击 **Show** 查看实际提交表单。

### 4. 用环境变量给脚本传参数

不要为每组参数复制一份脚本。可以在 Launcher 中添加 **Environment Variable** 字段，例如 `CITY_PARAM`、`DATASET` 或 `EXPERIMENT_NAME`，脚本通过环境变量读取这些值：

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${DATASET:?DATASET must be set by the launcher}"
: "${EXPERIMENT_NAME:?EXPERIMENT_NAME must be set by the launcher}"

cd "${OOD_PROJECT_DIR}"
python train.py \
  --dataset "${DATASET}" \
  --experiment "${EXPERIMENT_NAME}"
```

### 5. 从 Project Manager 启动作业

1. 在项目面板中选择 Launcher。
2. 点击 **Show**。
3. 选择目标主机分区和资源参数。
4. 填写环境变量或应用参数。
5. 点击 **Launch**。
6. 返回项目面板查看作业状态。

Project Manager 会在项目页面显示作业的 queued、running、failed 和 completed 状态，并定期刷新状态。提交后仍应打开日志检查程序是否真正完成；`completed` 只表示作业脚本正常退出，不代表训练结果正确。

### 6. 使用 Workflow 串联多个作业

当一个任务包含多个阶段时，可以将它们拆成多个 Launcher，再用 Workflow 设置依赖。例如：

```text
准备数据  →  训练模型  →  评测模型
```

操作步骤：

1. 为每个阶段创建一个 Launcher。可以使用 Launcher 卡片右上角的 **Copy Launcher** 复制已有表单，再修改 Script 和环境变量。
2. 确保每个 Launcher 的必要字段已经固定，尤其是集群、脚本和阶段所需参数。
3. 在项目面板点击 **New Workflow**，填写名称并保存。
4. 打开 Workflow，选择 Launcher 后点击 **Add Launcher**，依次加入各阶段。
5. 点击 **Connect Launchers**，按执行顺序选择上游和下游 Launcher，例如先选“准备数据”，再选“训练模型”。
6. 完成连接后再次点击 **Connect Launchers** 退出连线模式。
7. 点击 **Submit** 提交 Workflow。

下游 Launcher 只有在依赖的上游 Launcher 成功完成后才会进入运行状态。每次 Workflow 运行都会获得唯一的 `OOD_WORKFLOW_SYNC_KEY`，可以用它区分中间文件，避免多个 Workflow 同时运行时互相覆盖：

```bash
set -euo pipefail

: "${OOD_WORKFLOW_SYNC_KEY:?workflow key must be set}"
OUTPUT_DIR="${OOD_PROJECT_DIR}/outputs/${OOD_WORKFLOW_SYNC_KEY}"
mkdir -p "${OUTPUT_DIR}"
```

上游 Launcher 将结果写入这个目录，下游 Launcher 使用相同的 key 读取结果。不要让不同 Workflow 共用固定的 `output.csv` 或临时目录名。

### Project Manager 和 Job Composer 的区别


| 功能       | Job Composer                     | Project Manager                       |
| ------------ | ---------------------------------- | --------------------------------------- |
| 适合场景   | 提交一次或少量独立任务           | 长期项目、重复运行和多阶段流程        |
| 文件组织   | 一个任务目录                     | 项目目录，可保存脚本、输入和输出      |
| 表单       | 编辑`job.sh` 中的 `#SBATCH` 参数 | Launcher 表单，可用环境变量传参数     |
| 多阶段任务 | 需要手工拆分和提交               | Workflow 可视化设置依赖               |
| 结果追踪   | 通过 Jobs 页面和日志查看         | 项目面板集中查看 Launcher 和 Workflow |

已有 `job.sh` 的任务继续使用 Job Composer；需要反复改变参数或串联多个阶段时，建议迁移到 Project Manager。

官方教程：[Tutorials: Project Manager](https://osc.github.io/ood-documentation/latest/tutorials/tutorials-project-manager.html)。

## 提交和查看结果

### 提交

在 Job Composer 中：

1. 保存 `job.sh`。
2. 再次检查分区、资源、工作目录和日志路径。
3. 点击 **Submit**。
4. 记录页面显示的 Job ID。

提交成功只表示 Slurm 接受了作业，不代表程序已经成功完成。作业可能还在排队，也可能启动后因程序错误退出。

### 查看状态

在 OOD 的 **Jobs** 页面可以查看状态，也可以在控制节点命令行运行：

```bash
squeue -u "$USER"
scontrol show job <job-id>
```

常见状态：

- `PENDING`：等待资源或调度优先级；
- `RUNNING`：程序正在运行；
- `COMPLETED`：脚本退出码为 0；
- `FAILED`：脚本或程序返回错误；
- `CANCELLED`：作业被用户或管理员取消；
- `TIMEOUT`：达到 `--time` 限制。

排队时先检查资源申请是否过大，并查看 `squeue` 中的等待原因。不要为了绕过排队反复提交相同任务。

### 查看日志和最终状态

模板中的 `%x` 会替换为作业名，`%j` 会替换为作业号；数组任务还应使用 `%A-%a` 区分主作业和子任务。作业结束后查看日志：

```bash
cat training-12345.out
cat logs/evaluate-12345-7.out
```

使用 `sacct` 查看 Slurm 记录：

```bash
sacct -j <job-id> \
  --format=JobID,JobName,State,ExitCode,Elapsed,AllocTRES,NodeList
```

如果状态是 `COMPLETED` 但结果不正确，检查程序自己的日志和输出文件；Slurm 只判断脚本退出状态，不判断模型指标或输出内容。

### 取消和重新提交

```bash
scancel <job-id>
```

修改脚本后，建议先回到 Job Composer 保存，再提交一个新的 Job。不要直接修改已经运行任务的脚本并期待当前进程自动读取新内容。

## Script App 和命令行提交

已有 Slurm 脚本时，可以使用 Script App，或在控制节点命令行运行：

```bash
sbatch train.slurm
```

交互式测试可以使用 `srun`：

```bash
srun \
  --partition=epic-cluster-compute-a100-01 \
  --cpus-per-task=4 \
  --mem=16G \
  --gres=gpu:1 \
  --time=00:10:00 \
  bash
```

退出交互 shell 后，资源会释放。长时间运行的程序应写入 `sbatch` 脚本，而不是保持一个无人值守的 `srun` 会话。

## 常见问题

### 作业一直排队

运行 `squeue -u "$USER"` 和 `scontrol show job <job-id>`，确认目标分区、GPU 数量、内存和 CPU 申请合理。GPU 资源不足时只能等待或调整申请量，不能在作业内自行占用其他 GPU。

### 作业马上失败

优先检查：

1. `cd` 目录是否存在；
2. Python/Conda 环境路径是否正确；
3. 输入文件是否存在且有权限读取；
4. 日志中的最后一条错误；
5. `sacct` 的 `ExitCode` 和 `State`。

### 找不到 GPU

确认脚本包含 `#SBATCH --gres=gpu:N`，并且提交到了 GPU 主机分区。在作业内运行：

```bash
nvidia-smi -L
```
