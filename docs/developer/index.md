---
layout: default
title: 开发者文档
nav_order: 5
has_children: true
---

# 开发者与超级管理员文档

这里面向维护 Ansible、OOD 应用、监控配置和站点策略的开发者。管理员请从[管理员文档](../admin/index.md)开始。

1. [仓库与变更规则](01-repository.md)
2. [Ansible 架构](02-ansible.md)
3. [IAPP 开发](03-apps.md)
4. [文档维护](04-documentation.md)
5. [系统运维](05-operations.md)：服务、日志、节点、监控、配额和 BMC。
6. [超级管理员操作](06-superadmin.md)
7. [新增节点 Checklist](07-add-node-checklist.md)：计算节点从准备、声明到验收和交接的操作清单。
8. [计算节点环境安装](08-compute-node-environment.md)：Ubuntu GPU 计算节点在 Ansible 前的网络、Slurm、MUNGE、Docker 和 exporter 环境准备。

推荐阅读顺序是先看 source of truth 和发布流程，再看具体 role 或应用。已知错误统一查看[故障手册](../troubleshooting/index.md#developer-troubleshooting)。运行行为以 `ansible/` 和 `apps/` 为准，设计决策记录位于 `docs/superpowers/specs/`。
