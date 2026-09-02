---
layout: default
title: Association 强制导致正常用户无法提交
parent: 故障手册
nav_order: 13
---

<a id="association-enforcement-recovery"></a>

# Association 强制导致正常用户无法提交

先从 `slurm.conf` 移除 `AccountingStorageEnforce`，再执行：

```bash
scontrol reconfigure
```

不要清空 SlurmDBD 数据库、删除 Association 或 Slurm 状态目录。恢复提交后，先修复清单
或数据库状态，再重新启用强制。
