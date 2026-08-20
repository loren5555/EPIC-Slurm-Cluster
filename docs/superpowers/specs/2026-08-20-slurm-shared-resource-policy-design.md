# Slurm CPU 与 GPU 共享资源策略设计

日期：2026-08-20  
状态：用户已确认，待实施

## 目标

在 A100 与 RTX 4070 分区中取消内存调度阻塞，允许用户主动接受 CPU
超分，并为小任务提供 GPU shard，同时保留完整 GPU 作为 OOD 默认选项。

## Slurm 策略

- 两台主机均设置 `slurm_select_type_parameters: CR_Core`，使内存不再作为
  consumable resource 阻塞作业启动。
- A100 设置 `slurm_oversubscribe: "YES:4"`，RTX 4070 设置
  `slurm_oversubscribe: "YES:2"`。只有显式提交 `--oversubscribe` 的作业接受
  CPU core 共享。
- 保留 `ConstrainCores=yes` 与 `ConstrainDevices=yes`；沿用工作区中已完成的
  `ConstrainRAMSpace=no` 修改。
- 两个分区的 CPU billing weight 均为 `0.05`。

## GPU shard 策略

- A100 每张 GPU 配置 4 个 shard，共 32 个；每个 shard billing weight 为
  `0.25`。
- RTX 4070 每张 GPU 配置 2 个 shard，共 2 个；每个 shard billing weight 为
  `0.5`。
- 全局注册并记录 `gres/shard`；整卡与 shard 继续由 Slurm 作为同一物理 GPU
  的互斥分配方式管理。

## OOD 表单

- 使用单个 GPU resource 下拉框，默认值为 `gpu:1`。
- A100 提供无 GPU、1/4、1/2、3/4 共享 GPU，以及 1–8 张完整 GPU。
- RTX 4070 提供无 GPU、1/2 共享 GPU，以及 1 张完整 GPU。
- 不提供占满全部 shard 的共享选项；该需求使用完整 GPU。
- 增加默认关闭的 `Accept shared CPU cores` checkbox。勾选后提交
  `--oversubscribe`。
- 提交模板将下拉值严格映射为零个或一个 `--gres` 参数；高级参数不得再次
  提供 `--gres` 或 `--gpus*`，避免资源请求冲突。

## 验证

采用最小定向测试，覆盖主机策略字段、Slurm/GRES 模板声明、OOD 分区元数据、
GPU 下拉选项、GRES 映射和 CPU 共享 checkbox。只运行相关测试，不运行完整
测试套件；所有变更保留在工作区，不创建提交。

## 用户文档中的权重说明

在 `docs/user/queue.md` 的“哪些因素会影响顺序”中，紧接 Fair-share 原理说明
增加“资源如何计入 Fair-share”小节。使用表格列出两个分区的 CPU、完整 GPU
和 shard 权重，并给出 `4 CPU + 1 A100 = 1.2` 的计算示例。

该小节必须说明：权重用于累计 Fair-share 使用量，不是费用，也不会独立决定
某个任务能否立即运行。其数值与主机变量中的 `slurm_tres_billing_weights`
保持一致：CPU 为 `0.05`，完整 GPU 为 `1`，A100 shard 为 `0.25`，RTX 4070
shard 为 `0.5`。
