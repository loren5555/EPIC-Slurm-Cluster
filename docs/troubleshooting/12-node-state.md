---
layout: default
title: 节点处于 DOWN、DRAIN 或 INVALID_REG
parent: 故障手册
nav_order: 12
---

<a id="node-state-failure"></a>

# 节点处于 DOWN、DRAIN 或 INVALID_REG

```bash
scontrol show node <node>
sinfo -N -l --nodes=<node>
sudo journalctl -u slurmd --since today
```

确认节点通信、MUNGE、`slurmd`、时间同步和 host vars 资源声明。原因处理完后再恢复：

```bash
scontrol update nodename=<node> state=resume
```

不要把删除 `NodeName`、重建文件系统或清空 Slurm 状态作为普通恢复步骤。
