---
layout: default
title: GPU 共享与 CPU 超分
parent: 用户文档
nav_order: 4
---

# GPU 共享与 CPU 超分

Slurm支持将 GPU 划分为逻辑份额（GPU shard），也支持让多个作业共享 CPU
core。它们适合资源需求较小、希望更快启动的任务，但都可能影响性能稳定性。

## Shared GPU

### 什么是Shared GPU

Shared GPU 指的是把一张物理 GPU 划分成多个逻辑份额，让多个作业在同一
张卡上同时运行，但每个作业只使用其中一部分 GPU 资源。它和完整 GPU
的区别在于：完整 GPU 是一整张卡独占给单个作业，而 Shared GPU 是按 shard
进行切分，允许更灵活地混合多任务并发使用同一张卡。同一块GPU不会被同时分配给Shared与Full作业。

### 什么时候使用

如果程序只需要较小的 GPU 计算能力，可以申请 Shared GPU，而不是独占一整张
GPU。例如小规模推理、调试、数据预处理或短时间实验通常适合共享 GPU。

Shared GPU 是 Slurm 管理的逻辑 GPU 份额。一个 shard 只会分配给一个作业，
不会与另一个作业重复分配同一份 shard；但同一张物理 GPU 上的其他 shard
可能同时被其他作业使用。因此，<span style="color:red">共享 GPU 的计算吞吐和可用显存可能受到同卡其他作业影响</span>。需要稳定性能、较大显存或长时间训练时，应申请完整 GPU。

### 可用规格

| 分区 | 每张物理 GPU 的份额 | 可申请的 Shared GPU |
| --- | ---: | --- |
| A100 | 4 份 | `shard:1`、`shard:2`、`shard:3` |
| RTX 4070 | 2 份 | `shard:1` |

表单中的 **Shared GPU (1/4)** 表示 A100 的四分之一份额，**Shared GPU
(1/2)** 表示半张 RTX 4070。

### 在 OOD 中申请

在 Jupyter、Code Server、Script、TTYD 等 IAPP的提交表单中：

1. 选择目标分区（A100 或 RTX 4070）。
2. 在 **GPU resource** 中选择 **No GPU**、对应比例的 **Shared GPU**，
   或一个或多个完整 GPU。

### 在 Slurm 脚本中申请

完整 GPU 和 Shared GPU 使用不同的 GRES 名称，二者不能同时写入同一个作业：

```bash
# 一张完整 GPU
#SBATCH --gres=gpu:1

# 或一个 GPU shard（二选一，不能同时使用）
# #SBATCH --gres=shard:1
```

运行时可以使用 `nvidia-smi -L` 检查作业内可见的 GPU。程序是否支持在共享
GPU 上运行，仍取决于程序自身的显存和计算资源需求。

## CPU 超分

### 什么是CPU超分

CPU 超分允许多个作业共享同一个 CPU core。当同一core上存在其他工作负载时，任务
可能变慢或出现性能波动。

适合开启 CPU 超分的场景包括：

- GPU 计算占主导、CPU 只负责少量数据准备；
- 调试、交互式开发和短测试任务；
- 更看重尽快启动，而不是 CPU 性能。

CPU 性能敏感的任务，例如 CPU 密集型预处理、编译、科学计算或性能测试，
应关闭 CPU 超分。

### 在 OOD 中设置

表单中的 **Accept shared CPU cores** 选项用于控制 CPU 超分：

- 默认开启，任务会带上 `--oversubscribe`，可能更快启动；
- 取消勾选后，任务不接受共享 CPU core，CPU 性能通常更稳定，但可能需要
  等待更久。

### 在 Slurm 脚本中设置

在脚本中显式加入以下行即可接受 CPU 超分：

```bash
#SBATCH --cpus-per-task=4
#SBATCH --oversubscribe
```

不写 `--oversubscribe` 时，作业不会主动接受共享 CPU core。

## 选择建议

| 需求 | 建议 |
| --- | --- |
| 小模型推理或调试，GPU 需求较低 | Shared GPU；CPU 不敏感时可开启超分 |
| 长时间训练或需要稳定吞吐 | 完整 GPU；CPU 敏感时关闭超分 |
| 只做 CPU 计算 | 不申请 GPU；根据 CPU 负载决定是否超分 |
| 需要整张 GPU 的显存或稳定性能 | 使用 `gpu:1`，不要使用 shard |

无论选择哪种资源，都应先提交一个短测试任务，确认显存、运行时间和程序
吞吐符合预期，再提交正式实验。资源申请越准确，通常越容易排队，也更方便
其他用户共享集群。
