---
layout: default
title: 新增节点 Checklist
parent: 开发者文档
nav_order: 7
---

# 新增节点 Checklist

本清单面向 `epic-superadmins`，用于将一台计算节点接入 EPIC 集群。每次新增节点复制一份本清单到变更记录或 Pull Request，填写节点名、负责人和变更窗口，并逐项保留结果。不要直接在生产配置中试错。

## 1. 变更准备

- [ ] 确认节点用途、负责人、变更窗口和用户开放时间。
- [ ] 按 `epic-cluster-compute-<型号>-<序号>` 确定稳定主机名；主机名一经被用户授权或作业脚本引用，不再随 IP 地址改变。
- [ ] 确认节点归入 `controlled_compute_nodes` 或 `free_compute_nodes`；只有 GPU 节点加入 `gpu_nodes`。
- [ ] 记录 CPU、内存、GPU 型号与数量、本地磁盘、管理地址和 BMC 信息。
- [ ] 明确失败回退条件：新节点保持 `DRAIN` 或从 inventory 移除，不影响现有节点、分区和 Association。

## 2. 主机和运行时

以[计算节点环境安装](08-compute-node-environment.md)中的显式命令完成下列 Ansible 前准备，并记录实际软件版本和镜像 digest。

- [ ] 配置固定地址、DNS 或 `/etc/hosts`，确认控制节点和新节点能够按稳定主机名双向解析。
- [ ] 配置时间同步，确认控制节点与新节点时间一致。
- [ ] 建立超级管理员 SSH 访问，确认 Ansible 能使用 inventory 中的管理账户连接并提权。
- [ ] 安装与集群兼容的 MUNGE 和 Slurm 版本，分发 MUNGE key，并确认 `munge -n | unmunge` 成功。
- [ ] 创建 Slurm 日志与 spool 目录，确认属主、权限和磁盘空间满足现有节点约定。
- [ ] 挂载节点需要的 `/home`、`/workspace`、`/data` 或 OOD 上下文路径；不要把本地临时盘误标为持久存储。
- [ ] GPU 节点手工安装并确认 NVIDIA 驱动、容器运行时及所需 exporter；Ansible 不负责隐式安装驱动或跨发行版软件包。

## 3. 仓库声明

- [ ] 在 `ansible/inventory/hosts.yml` 的正确计算节点组中加入稳定主机名；GPU 节点同时加入 `gpu_nodes`。
- [ ] 新建 `ansible/inventory/host_vars/<节点名>.yml`，按实测硬件填写 Slurm CPU、内存和 GRES 等资源数据。
- [ ] 在 `ansible/vars/slurm_partitions.yml` 新增与节点同名的分区，填写 `host`、`management_class`、`allowed_accounts`、`allowed_users` 和 `denied_users`。
- [ ] 检查 `ansible/vars/users.yml` 中需要访问该节点的 `ssh_access`；SSH 访问与 Slurm 提交权限分别声明，不能互相替代。
- [ ] 如需新的 Account 或 QoS，先在对应声明文件中定义，再为分区建立 Association；不要在生产数据库中留下未声明的手工条目。
- [ ] 确认 inventory 驱动的 Prometheus target、OOD 节点入口和 GPU exporter 选择只包含预期节点。

## 4. 分阶段部署

- [ ] 新节点先保持不可调度，避免配置未完成时接收用户作业。
- [ ] 依次执行与本次变更有关的最小工作包：身份、SSH、SlurmDBD/Association、Slurm、监控、OOD 和配额；不要首先运行完整 `site.yml`。
- [ ] 每个工作包先执行 `--syntax-check`，再执行 `--check --diff`，审阅只涉及预期主机和配置后再正式运行。
- [ ] 确认 `munge`、`slurmd`、`node_exporter` 以及 GPU 节点所需 exporter 正常运行。
- [ ] 在控制节点执行 `scontrol reconfigure` 后，确认新节点资源与 host vars 一致，且没有 `INVALID_REG`、`DOWN` 或意外的分区状态。

## 5. 验收

- [ ] 使用 `sinfo -N -l`、`scontrol show node <节点名>` 和 `scontrol show partition <节点名>` 检查节点、资源和分区。
- [ ] 使用允许的测试账户提交最小 CPU 作业，确认调度、标准输出、工作目录和存储访问正常。
- [ ] GPU 节点提交最小 GPU 作业，确认 `CUDA_VISIBLE_DEVICES`、驱动、GPU 数量和 Slurm GRES 分配一致。
- [ ] 确认不在允许范围内的用户或 Account 无法向该分区提交作业。
- [ ] 在 Prometheus/Grafana 中确认节点在线、标签正确且没有重复 target；GPU 节点同时确认 GPU 指标。
- [ ] 从 OOD 确认节点入口、Interactive App、作业提交和 Remote Files 只暴露预期资源。
- [ ] 检查 Slurm、MUNGE、OOD 和 exporter 日志，确认没有持续错误后再将节点恢复为可调度状态。

## 6. 回退与交接

- [ ] 验收失败时立即将节点设为 `DRAIN` 并记录原因；不要删除现有 SlurmDBD 数据、Association 或其他节点配置。
- [ ] 回退本次新增的 inventory、host vars、分区和授权声明，重新收敛受影响的最小工作包。
- [ ] 在变更记录或 Pull Request 中保存执行命令、关键输出、异常、处理结果和最终开放时间。
- [ ] 更新节点资产信息、BMC 凭据保管位置和维护负责人；凭据不得写入仓库。
- [ ] 通知管理员新节点的分区名、资源范围、允许用户或 Account，以及已知限制。

相关背景见[Ansible 架构](02-ansible.md)、[系统运维](05-operations.md)、[超级管理员操作](06-superadmin.md)和[计算节点环境安装](08-compute-node-environment.md)。
