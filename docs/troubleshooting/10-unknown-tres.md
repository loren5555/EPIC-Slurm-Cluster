---
layout: default
title: 启用记账后出现 Unknown TRES
parent: 故障手册
nav_order: 10
---

# 启用记账后出现 Unknown TRES

检查 `slurm.conf` 是否声明 `AccountingStorageTRES=gres/gpu`，SlurmDBD 中是否已有当前
cluster 记录，以及 `slurmctld` 与 `slurmdbd` 是否为兼容的主版本：

```bash
scontrol show config | grep -E 'AccountingStorage(TRES|Type)'
sacctmgr show cluster
slurmctld -V
slurmdbd -V
```

先恢复 TRES 与版本一致性，再重载配置；不要删除既有记账数据。
