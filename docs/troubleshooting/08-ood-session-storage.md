---
layout: default
title: OOD 会话目录不可用
parent: 故障手册
nav_order: 8
---

# OOD 会话目录不可用

OOD 会话目录使用 `/srv/epic/ood`，与规划中的用户共享 `/data` 是两个独立系统。先在
发生问题的主机检查 automount 和实际挂载：

```bash
systemctl status srv-epic-ood.automount --no-pager
mountpoint /srv/epic/ood
```

再在导出端检查 `exportfs -v`。只修复会话挂载，不要为了恢复 OOD 同时重启 Slurm、SSH
或无关计算任务。恢复后实际启动一个 IAPP 验收。
