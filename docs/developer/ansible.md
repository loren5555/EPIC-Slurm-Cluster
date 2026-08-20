---
layout: default
title: Ansible 架构
parent: 开发者文档
nav_order: 2
---

# Ansible 架构

## 收敛顺序

`site.yml` 按依赖顺序执行身份、SSH、SlurmDBD、Account/Association、管理员权限、Slurm 强制策略、Grafana、监控、OOD 和配额。身份必须先于 SSH；记账和 Association 必须先于权限强制；监控和 OOD 依赖已经存在的 Slurm 与主机运行时。

常规修改先执行：

```bash
ansible-playbook playbooks/<name>.yml --syntax-check
ansible-playbook playbooks/<name>.yml --check --diff
ansible-playbook playbooks/<name>.yml
```

## 数据流

- Python filter 只计算计划，不修改主机。
- role task 负责读取现状、显示计划、阻止危险变更，再执行收敛。
- Jinja template 生成系统配置、OOD 菜单和监控 targets。
- `slurm_partitions.yml`、`users.yml` 和 host vars 是 OOD 主机菜单的输入；SlurmDBD Association 是授权的最终来源。

新增节点时先加入 inventory 和 host vars，再声明同名分区、授权、监控 target 和 OOD 入口，最后运行最小 CPU/GPU 作业验收。Ansible 不负责安装跨发行版的软件包；SlurmDBD、Prometheus、Grafana、OOD 和 GPU exporter 的手工安装边界见[超级管理员文档](superadmin.md)。
