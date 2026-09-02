---
layout: default
title: 故障手册
nav_order: 6
has_children: true
---

# 故障手册

本手册按故障现象拆分为独立页面。先选择最接近的现象，只处理对应组件；不要为了一个
局部错误重启整个集群。涉及密码、私钥、Vault、MUNGE key、数据库或 BMC 凭据时，
不要将其写入 Issue、文档或日志附件。

<a id="user-troubleshooting"></a>

## 用户问题

- [作业一直排队](01-job-pending.md)
- [作业立即失败](02-job-failed.md)
- [Interactive App 无法连接](03-interactive-app.md)
- [GPU 不可见或数量不对](04-gpu-visibility.md)
- [磁盘空间不足](05-disk-space.md)

<a id="admin-troubleshooting"></a>

## 管理员问题

- [用户配置工作包失败](06-user-onboarding.md)
- [作业或分区异常](07-job-partition.md)
- [OOD 会话目录不可用](08-ood-session-storage.md)

<a id="developer-troubleshooting"></a>

## 开发者与部署问题

- [SlurmDBD 或 MariaDB 无法连接](09-slurmdbd.md)
- [启用记账后出现 Unknown TRES](10-unknown-tres.md)
- [Prometheus target 或 exporter 下线](11-monitoring-target.md)
- [节点处于 DOWN、DRAIN 或 INVALID_REG](12-node-state.md)
- [Association 强制导致正常用户无法提交](13-association-enforcement.md)
- [Identity 预检报 UID/GID 冲突](14-identity-conflict.md)
- [SSH 预检报受管用户不存在](15-ssh-preflight.md)

仍无法解决时，提交 Issue，并附上主机、分区、作业号、失败 task、复现步骤和经过脱敏的
必要日志。
