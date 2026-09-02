---
layout: default
title: 磁盘空间不足
parent: 故障手册
nav_order: 5
---

# 磁盘空间不足

```bash
df -h /home /workspace
quota -s
```

先清理缓存和可再生成的中间文件，不要删除别人的目录或绕过配额。A100 的 `/home` 和
`/workspace` 都有限额，状态会显示在 OOD 首页；当前不再通过 Slurm Prolog 提示超限。

规划中的共享 `/data` 尚未上线。重要结果应复制到实验室认可的独立存储，不能把
`/workspace` 当成唯一副本。
