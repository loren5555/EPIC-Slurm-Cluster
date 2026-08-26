---
layout: default
title: 文档导航
nav_order: 2
---

# EPIC 集群文档

EPIC 集群通过 Open OnDemand 提供网页入口，通过 Slurm 提交和管理计算任务。每台计算主机有自己的 Slurm 分区，用户应在提交时明确选择目标主机。

<span style="color:red">必须将控制节点的ip注册至本地的hosts文件才能正常访问网站</span>
```
222.20.99.125 epic-cluster-controller-01
```

## 按读者查找

- **用户**：从[用户文档](user/index.md)开始，了解登录、提交任务、存储和排障。
- **管理员**：从[管理员文档](admin/index.md)开始，了解日常操作、部署、权限、监控和 OOD。
- **开发者**：从[开发者文档](developer/index.md)开始，了解仓库、Ansible、IAPP 和文档维护。

## 常用入口

- [用户快速开始](user/quick-start.md)
- [提交 Interactive App 和批处理任务](user/jobs.md)
- [管理员日常操作](admin/operations.md)
- [集群部署流程](admin/deployment.md)
- [IAPP 开发](developer/apps.md)

[提交 Issue](https://github.com/loren5555/EPIC-Slurm-Cluster/issues/new/choose) 前，请先查看对应读者文档并附上最小复现信息。
