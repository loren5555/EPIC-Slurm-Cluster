---
layout: default
title: 其它功能
parent: 用户文档
nav_order: 7
---

# 命令行访问

本页说明通过 OOD 获取控制节点命令行。

控制节点用于 OOD、Slurm 客户端和集群管理命令。普通用户可以通过OOD的命令行访问打开控制节点 Shell：

1. 登录 OOD。
2. 打开上方 **Clusters → EPIC Slurm Cluster Shell Access**。
3. 等待终端会话启动，在浏览器中使用控制节点命令行。

在控制节点终端中可以运行：

```bash
hostname
sinfo -s
squeue -u "$USER"
sacct -j <job-id> --format=JobID,State,Elapsed,AllocTRES
```

控制节点 Shell 适合查看队列、提交任务、检查作业记录和准备文件。

注意获取的命令行是运行在控制节点的，计算任务仍应提交到 Slurm 分区，不要把训练程序直接放在控制节点上运行，一定会被干掉。

如果已经按上一节配置了本地 SSH，也可以直接连接控制节点：

```bash
ssh epic-controller
```