---
layout: default
title: 管理员可用命令
parent: 管理员文档
nav_order: 3
---

# 管理员可用命令

业务管理员的命令权限由控制节点 `/etc/sudoers.d/epic-operators` 管理。Git 仓库操作和 Ansible 工作包均采用固定路径、固定参数和固定顺序。

## 更新部署仓库

```bash
sudo /usr/bin/git \
  -C /srv/epic/repos/EPIC-Slurm-Cluster \
  status

sudo /usr/bin/git \
  -C /srv/epic/repos/EPIC-Slurm-Cluster \
  log --oneline -n 20

sudo /usr/bin/git \
  -C /srv/epic/repos/EPIC-Slurm-Cluster \
  pull --ff-only origin main
```

先查看仓库状态和最近提交，再使用 fast-forward 方式同步 `main`。

## 执行 Ansible 工作包

所有工作包使用同一个 Ansible 配置文件：

```text
ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg
```

业务管理员可执行的工作包如下：


| 工作包                   | 用途                                        |
| -------------------------- | --------------------------------------------- |
| `users.yml`              | 同步 Linux 用户、UID/GID 和 access group    |
| `ssh_access.yml`         | 根据用户授权同步集群 SSH key                |
| `slurm.yml`              | 发布 Slurm 配置                             |
| `slurm_associations.yml` | 发布 Account、QoS 和分区 Association        |
| `disk_quotas.yml`        | 发布已初始化文件系统的用户配额              |
| `monitoring.yml`         | 发布监控配置和服务状态                      |
| `grafana.yml`            | 发布 Grafana 配置和仪表盘 provisioning      |
| `ood.yml`                | 发布 OOD 门户、IAPP 和 Remote Files 配置    |
| `user_onboarding.yml`    | 一次完成身份、SSH、Slurm、配额和 OOD 收敛   |

每个工作包有两种固定调用方式：检查模式和正式执行。以身份同步为例：

```bash
sudo /usr/bin/env \
  ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg \
  /usr/bin/ansible-playbook \
  /srv/epic/repos/EPIC-Slurm-Cluster/ansible/playbooks/users.yml \
  --check

sudo /usr/bin/env \
  ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg \
  /usr/bin/ansible-playbook \
  /srv/epic/repos/EPIC-Slurm-Cluster/ansible/playbooks/users.yml
```

其它工作包沿用相同格式，只替换 playbook 文件名。命令参数由 sudoers 精确匹配，部署时使用仓库中已经审核的清单。

### 新用户一键配置

用户清单合并到控制节点的 `main` 分支后，可使用组合 playbook 一次完成身份、SSH、
Slurm Association、磁盘配额和 OOD 用户配置：

```bash
sudo /usr/bin/env \
  ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg \
  /usr/bin/ansible-playbook \
  /srv/epic/repos/EPIC-Slurm-Cluster/ansible/playbooks/user_onboarding.yml \
  --check

sudo /usr/bin/env \
  ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg \
  /usr/bin/ansible-playbook \
  /srv/epic/repos/EPIC-Slurm-Cluster/ansible/playbooks/user_onboarding.yml
```

该组合按以下固定顺序执行：

```text
users.yml → ssh_access.yml → slurm_associations.yml → disk_quotas.yml → ood.yml
```

完成后，用户可以在已授权分区提交 Slurm 任务，并能在 OOD 中看到对应主机和
Remote Files 配置。OOD 密码仍使用本页末尾的命令单独设置。

## 修改 OOD 密码

管理员可以为任意语法合法的 OOD 用户名创建或重置密码，不需要先重新发布
sudoers 用户名单：

```bash
sudo /usr/bin/htpasswd /etc/ood/auth/htpasswd <username>
```

密码输入保持交互式，密码哈希只写入控制节点的 htpasswd 文件。OOD 密码与
Linux 密码、SSH 密钥和 Slurm 权限相互独立。
