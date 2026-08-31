---
layout: default
title: 开发者文档
nav_order: 5
has_children: true
---

# 开发者与超级管理员文档

这里面向维护 Ansible、OOD 应用、监控配置和站点策略的开发者。管理员请从[管理员文档](../admin/index.md)开始。

- [仓库与变更规则](repository.md)
- [Ansible 架构](ansible.md)
- [系统运维](operations.md)：服务、日志、节点、监控、配额和 BMC。
- [超级管理员操作](superadmin.md)
- [IAPP 开发](apps.md)
- [文档维护](documentation.md)

推荐阅读顺序是先看 source of truth 和发布流程，再看具体 role 或应用。运行行为以 `ansible/` 和 `apps/` 为准，设计决策记录位于 `docs/superpowers/specs/`。
