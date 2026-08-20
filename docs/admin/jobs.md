# 任务管理

管理员负责查看任务、处理异常作业、协助用户调整资源申请，并根据实验室规则维护任务秩序。

## 查看任务

```bash
squeue	# 查看当前队列

squeue -u <username>	# 查看特定用户提交的任务

scontrol show job <job-id>	# 查看任务详细信息

sacct -j <job-id> \	 # 查看任务状态
  --format=JobID,User,Account,Partition,State,ExitCode,Elapsed,AllocTRES
```

重点关注：

- 用户和 Account；
- 目标分区；
- CPU、内存和 GPU 申请；
- 任务状态和等待原因；
- 实际运行时间与申请时长的差异。

## 取消和重排任务

```bash
scancel <job-id>
scontrol requeue <job-id>
```

取消前记录原因并通知用户。重排适用于脚本可重复、输入数据完整的任务；修改脚本后重新提交比直接重排更合适。

## 任务统计

```bash
sacct --starttime=today \
  --format=JobID,User,Account,Partition,State,Elapsed,AllocTRES
sreport cluster AccountUtilizationByUser start=month
sshare --all --long
sprio
```

`sacct` 用于查看作业历史，`sreport` 用于 Account 和用户使用量汇总，`sshare` 用于 Fair-share 状态，`sprio` 用于解释待运行任务的优先级组成。

## 资源使用沟通

管理员可以根据任务记录向用户反馈：

1. 先提交小规模测试；
2. 根据测试结果估算正式任务时间；
3. 只申请实际需要的资源；
4. 为长任务准备日志和断点保存；
5. 任务完成后释放 Interactive App 和临时资源。

节点 `DOWN`、`DRAIN`、Slurm 服务故障、数据库故障和日志排查转交[开发者文档](../developer/index.md)。
