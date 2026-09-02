---
layout: default
title: GPU 不可见或数量不对
parent: 故障手册
nav_order: 4
---

# GPU 不可见或数量不对

确认作业提交到 GPU 主机分区，并使用 `--gres=gpu:N` 或 OOD 的 GPU 字段申请。在作业
内运行：

```bash
echo "$CUDA_VISIBLE_DEVICES"
nvidia-smi -L
```

A100 的普通 SSH 会话按设计不能直接使用 GPU。应在该终端提交 Slurm 作业，而不是修改
设备权限。管理员维护 A100 GPU 时使用：

```bash
sudo systemd-run --pty --slice=system.slice bash
```

节点级隔离说明见
[A100 节点基线](../developer/09-a100-node-baseline.md#ssh-登录会话与-gpu)。
