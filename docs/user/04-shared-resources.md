---
layout: default
title: GPU 共享与 CPU 分配
parent: 用户文档
nav_order: 4
---

# GPU 共享与 CPU 分配

集群支持将 GPU 划分为逻辑份额（GPU shard）。CPU 超分已关闭，Slurm 按 CPU core 分配资源，同一个 core 不会同时分配给多个作业。

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

## CPU 分配

所有分区关闭 CPU 超分。多个作业仍可以在同一节点并行，但使用各自分配的 CPU
core；GPU shard 的共享方式不受影响。

OOD 表单只需填写 **CPU cores**，不再提供 CPU 超分开关。轻量 debug 可以申请
1–2 个 CPU，计算任务按实际并行度申请；资源不足时等待调度。

Slurm 脚本只需声明所需 CPU 数量，不要添加 `--oversubscribe`：

```bash
#SBATCH --cpus-per-task=4
```

旧脚本应删除 `#SBATCH --oversubscribe`。不要用作业级
`scontrol update ... OverSubscribe=NO` 代替删除选项；在当前控制器版本中，
显式设置该值会要求空闲节点，与默认的 `OverSubscribe=OK` 不同。
修改脚本不会更新已经提交的作业。

这里的独立分配针对 Slurm 作业，不代表对普通 SSH 进程或整机性能作出保证。

## 选择建议

| 需求 | 建议 |
| --- | --- |
| 小模型推理或调试，GPU 需求较低 | Shared GPU；按调试需要申请少量 CPU |
| 长时间训练或需要稳定吞吐 | 完整 GPU；按实际并行度申请 CPU |
| 只做 CPU 计算 | 不申请 GPU；按实际并行度申请 CPU |
| 需要整张 GPU 的显存或稳定性能 | 使用 `gpu:1`，不要使用 shard |

无论选择哪种资源，都应先提交一个短测试任务，确认显存、运行时间和程序
吞吐符合预期，再提交正式实验。资源申请越准确，通常越容易排队，也更方便
其他用户共享集群。
