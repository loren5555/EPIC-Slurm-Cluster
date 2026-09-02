---
layout: default
title: 新增节点 Checklist
parent: 开发者文档
nav_order: 7
---
# 新增节点 Checklist

本清单面向 `epic-superadmins`，用于将一台计算节点接入 EPIC 集群。记录节点名、负责人
和计划开放时间即可；验收以实验室实际可用为准，不要求工业部署式的重复证明。

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
- [ ] 挂载节点需要的 `/home`、`/workspace` 和 OOD 上下文路径；共享 `/data` 尚未上线，上线后按[共享存储设计](10-shared-storage.md)单独验收。不要把本地临时盘误标为持久存储。
- [ ] GPU 节点手工安装并确认 NVIDIA 驱动、容器运行时及所需 exporter；Ansible 不负责隐式安装驱动或跨发行版软件包。
- [ ] 按安装文档准备 OOD IAPP 运行时，确认 `/usr/local/bin/code-server`、`/usr/bin/ttyd`、`/opt/jupyterlab/bin/jupyter-lab` 和 `/opt/tensorboard/bin/tensorboard` 均可执行，并记录版本。

## 3. 仓库声明

- [ ] 在 `ansible/inventory/hosts.yml` 的正确计算节点组中加入稳定主机名；GPU 节点同时加入 `gpu_nodes`。
- [ ] 新建 `ansible/inventory/host_vars/<节点名>.yml`，按实测硬件填写 Slurm CPU、内存和 GRES 等资源数据。
- [ ] 在 `ansible/vars/slurm_partitions.yml` 新增与节点同名的分区，填写 `host`、`management_class`、`allowed_accounts`、`allowed_users` 和 `denied_users`。
- [ ] 检查 `ansible/vars/users.yml` 中需要访问该节点的 `ssh_access`；SSH 访问与 Slurm 提交权限分别声明，不能互相替代。
- [ ] 如需新的 Account 或 QoS，先在对应声明文件中定义，再为分区建立 Association；不要在生产数据库中留下未声明的手工条目。
- [ ] 确认 inventory 驱动的 Prometheus target、OOD 节点入口和 GPU exporter 选择只包含预期节点。

## 4. 分阶段部署

- [ ] 新节点先保持不可调度，避免配置未完成时接收用户作业。
- [ ] 先正式运行身份工作包；如果预检报同名账号的 UID/GID 不一致，使用[故障手册：UID/GID 冲突](../troubleshooting/14-identity-conflict.md)。
- [ ] 身份收敛成功后再运行 SSH 工作包；如果报受管用户不存在，使用[故障手册：SSH 预检缺少用户](../troubleshooting/15-ssh-preflight.md)。
- [ ] 继续依次执行 SlurmDBD/Association、Slurm、监控、OOD 和配额的最小工作包；不要首先运行完整 `site.yml`。
- [ ] 每个工作包执行一次 `--check --diff`，审阅只涉及预期主机和配置后再正式运行。
- [ ] 确认 `munge`、`slurmd`、`node_exporter` 以及 GPU 节点所需 exporter 正常运行。
- [ ] 在控制节点执行 `scontrol reconfigure` 后，确认新节点资源与 host vars 一致，且没有 `INVALID_REG`、`DOWN` 或意外的分区状态。

## 5. 验收

- [ ] 使用 `sinfo -N -l`、`scontrol show node <节点名>` 和 `scontrol show partition <节点名>` 检查节点、资源和分区。
- [ ] 使用允许的测试账户提交最小 CPU 作业，确认调度、标准输出、工作目录和存储访问正常。
- [ ] GPU 节点提交最小 GPU 作业，确认 `CUDA_VISIBLE_DEVICES`、驱动、GPU 数量和 Slurm GRES 分配一致。
- [ ] 在 Prometheus/Grafana 中人工确认节点在线；GPU 节点同时看一眼 GPU 指标。
- [ ] 从 OOD 实际启动一个本次需要的 IAPP，确认节点入口、反向代理和作业提交可用；
  该结果同时作为应用发布、运行时和基本 OOD 配置的验收，不再拆成重复代码测试。
- [ ] 将节点恢复为可调度状态；只有实际失败时再查看对应服务日志。

## 6. 回退与交接

- [ ] 验收失败时立即将节点设为 `DRAIN` 并记录原因；不要删除现有 SlurmDBD 数据、Association 或其他节点配置。
- [ ] 回退本次新增的 inventory、host vars、分区和授权声明，重新收敛受影响的最小工作包。
- [ ] 在变更记录或 Pull Request 中保存执行命令、关键输出、异常、处理结果和最终开放时间。
- [ ] 更新节点资产信息、BMC 凭据保管位置和维护负责人；凭据不得写入仓库。
- [ ] 通知管理员新节点的分区名、资源范围、允许用户或 Account，以及已知限制。

相关背景见[Ansible 架构](02-ansible.md)、[系统运维](05-operations.md)、[超级管理员操作](06-superadmin.md)、[计算节点环境安装](08-compute-node-environment.md)和[故障手册](../troubleshooting/index.md)。
