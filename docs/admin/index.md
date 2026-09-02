---
layout: default
title: 管理员文档
nav_order: 4
has_children: true
---

# 管理员文档

管理员负责使用者、作业和资源使用秩序。

- [用户管理](users.md)：新增用户、调整用户访问范围、设置 Slurm Account 和 OOD 密码。
- [任务管理](jobs.md)：查看、取消、重排和统计用户作业，处理排队和资源申请问题。
- [管理员命令](commands.md)：同步部署仓库、执行固定 Ansible 工作包和修改 OOD 密码。
- [故障手册](../troubleshooting/index.md#admin-troubleshooting)：用户配置、作业、分区和系统问题的统一查询入口。

管理员通过 Slurm 命令处理作业，通过声明清单提出用户和访问权限变更。涉及主机、服务或系统配置的问题提交给开发者处理。
