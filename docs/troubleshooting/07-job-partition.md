---
layout: default
title: 作业或分区异常
parent: 故障手册
nav_order: 7
---

# 作业或分区异常

```bash
scontrol show job <job-id>
sacct -j <job-id> --format=JobID,User,Account,Partition,State,ExitCode,Elapsed,AllocTRES
sinfo -N -l
```

资源申请或脚本问题由管理员协助用户修正。节点 `DOWN`、`DRAIN` 或 `INVALID_REG` 转到
[节点状态故障](12-node-state.md)；正常用户被 Association 拒绝时转到
[Association 强制恢复](13-association-enforcement.md)。
