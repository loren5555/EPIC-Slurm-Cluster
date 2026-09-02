---
layout: default
title: 实验室部署操作
parent: Other
nav_order: 1
---

# 实验室部署操作

本页恢复旧部署说明中仍适用于当前仓库的具体操作。目标是让集群完成一次真实可用
调用，不包含高可用、自动故障转移、无人值守恢复或重复运行证明。

## 部署前

先在群内通知预计开始、影响范围和预计恢复时间。简单模板：

```text
[EPIC 维护] HH:MM 开始维护 <服务/节点>，期间 <影响>，预计 HH:MM 恢复。
恢复后会另行通知；正在运行重要任务的用户请联系管理员。
```

在控制节点确认当前状态，并记录异常；已有异常未解释时不要继续扩大变更范围。

```bash
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
ansible all -m ping
scontrol ping
sinfo -N -l
squeue
```

## 一次部署顺序

按依赖关系执行。每一步只需预览一次、应用一次，再用真实入口验收一次。

```bash
# 1. 身份、登录与 Slurm 基础配置
ansible-playbook playbooks/users.yml --check --diff
ansible-playbook playbooks/users.yml
ansible-playbook playbooks/ssh_access.yml --check --diff
ansible-playbook playbooks/ssh_access.yml
ansible-playbook playbooks/slurm.yml --check --diff
ansible-playbook playbooks/slurm.yml

# 2. 数据库软件已手工准备后，部署记账配置
ansible-playbook playbooks/slurmdbd.yml --check --diff
ansible-playbook playbooks/slurmdbd.yml

# 3. 先建立 Account/Association，再启用依赖它们的提交限制
ansible-playbook playbooks/slurm_associations.yml --check --diff
ansible-playbook playbooks/slurm_associations.yml

# 4. 监控软件已手工准备后，发布服务配置
ansible-playbook playbooks/monitoring.yml --check --diff
ansible-playbook playbooks/monitoring.yml
ansible-playbook playbooks/grafana.yml --check --diff
ansible-playbook playbooks/grafana.yml

# 5. 计算节点运行时已手工准备后，发布 OOD 与 IAPP
ansible-playbook playbooks/ood.yml --check --diff
ansible-playbook playbooks/ood.yml
```

不要在 Association 尚未完整时启用 `AccountingStorageEnforce=associations`。若该设置
阻断正常用户，按[故障手册](../troubleshooting/13-association-enforcement.md)
临时撤回；不要删除数据库或 Association。

## 最小验收

选择当前实际分区完成一次 CPU 作业；GPU 节点再完成一次单 GPU 作业：

```bash
srun --partition=<cpu-or-gpu-partition> --time=00:05:00 hostname
srun --partition=<gpu-partition> --gres=gpu:1 --time=00:05:00 nvidia-smi -L
sacctmgr ping
```

随后从 OOD 启动一个实际 IAPP，并在 Grafana/Prometheus 页面人工确认目标可见。IAPP
成功启动已经同时证明应用发布、对应运行时、OOD、Slurm 和基本会话路径可用，不再为
这些前提分别编写代码测试。

完成后通知恢复：

```text
[EPIC 维护完成] <服务/节点> 已恢复；已人工验证 <作业/IAPP/页面>。如仍有问题请附作业号和时间联系管理员。
```
