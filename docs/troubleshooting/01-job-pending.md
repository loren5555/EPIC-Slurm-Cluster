---
layout: default
title: 作业一直排队
parent: 故障手册
nav_order: 1
---

# 作业一直排队

```bash
squeue -u "$USER"
scontrol show job <job-id>
```

检查目标分区、等待原因、GPU 数量、CPU、内存和时限。资源不足时只能等待或减少申请
量，不要反复提交同一作业。管理员需要进一步判断时转到[作业或分区异常](07-job-partition.md)。
