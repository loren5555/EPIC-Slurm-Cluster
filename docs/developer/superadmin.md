---
layout: default
title: 超级管理员操作
parent: 开发者文档
nav_order: 6
---

# 超级管理员操作

本页面向 `epic-superadmins` 成员，负责系统安装、凭据、管理员权限、首次初始化、完整站点收敛和紧急恢复。日常业务管理员请使用[管理员文档](../admin/index.md)，不要把本页命令加入业务管理员的固定权限范围。

## 权限边界

超级管理员负责：

- 安装和升级 Slurm、MUNGE、MariaDB、SlurmDBD、Prometheus、Grafana、OOD、Docker 和 GPU exporter；
- 管理 Ansible Vault、数据库密码、部署密钥和 BMC 凭据；
- 管理 `epic-superadmins`、`epic-operators` 和 `/etc/sudoers.d/epic-operators`；
- 首次初始化网络、NFS、文件系统配额和控制节点；
- 执行 `site.yml`、数据库迁移和紧急回滚。

业务管理员不拥有上述权限。GitHub 分支保护和 PR 审核是持久配置变更的审计边界。

## 管理员权限收敛

管理员名单位于 `ansible/vars/administrators.yml`，用户身份必须先存在于 `ansible/vars/users.yml`。新增或撤销管理员时：

1. 先修改并合并身份和管理员清单；
2. 保留被撤销管理员的用户条目；
3. 运行管理员工作包检查和部署；
4. 用户重新登录，使新的 Linux 组成员关系生效；
5. 如果用户离开集群，再单独处理身份和 SSH 权限。

```bash
sudo /usr/bin/env \
  ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg \
  /usr/bin/ansible-playbook \
  /srv/epic/repos/EPIC-Slurm-Cluster/ansible/playbooks/administrators.yml \
  --check

sudo /usr/bin/env \
  ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg \
  /usr/bin/ansible-playbook \
  /srv/epic/repos/EPIC-Slurm-Cluster/ansible/playbooks/administrators.yml
```

## 软件和凭据

软件安装必须先检查候选版本和模拟结果，确认不会替换 Slurm、MUNGE、驱动或内核。MariaDB 和 SlurmDBD 使用 Ansible Vault 保存密码：

```bash
sudo apt update
apt-cache policy mariadb-server slurmdbd
sudo apt-get --simulate install mariadb-server slurmdbd
openssl rand -hex 32
ansible-vault create ansible/vars/secrets.yml
```

软件安装完成后，再由 `slurmdbd.yml` 配置数据库和服务。`/etc/slurm/slurmdbd.conf` 必须是 `slurm:slurm 0600`，MariaDB 只监听控制节点本机。

硬件维护需要通过堡垒机访问 BMC。账户和密码独立于集群用户体系：

```bash
ssh -N -L 8443:192.168.100.2:443 maintain@222.20.76.74
```

浏览器打开 `https://localhost:8443`。BMC 密码不写入仓库或 Ansible 变量。

Prometheus、Grafana、OOD、node_exporter、nvitop-exporter 和 DCGM Exporter 同样遵循“软件手工安装，Ansible 管理配置”的边界。Ansible 不应隐式安装 NVIDIA 驱动、Docker runtime 或跨发行版软件包。

## 首次部署顺序

完整站点收敛的依赖顺序如下：

1. 手工准备主机、身份、Slurm、MUNGE、软件包和运行时；
2. `users.yml`：同步身份；
3. `ssh_access.yml`：生成和分发受管 SSH key；
4. `slurmdbd.yml`：配置 MariaDB/SlurmDBD；
5. `slurm_associations.yml`：创建 Account、QoS 和分区 Association；
6. `administrators.yml`：配置管理员权限；
7. `slurm.yml`：最后开启记账连接、Association 强制和 Fair Tree；
8. `grafana.yml`、`monitoring.yml`：配置监控和展示；
9. `ood.yml`：最后发布门户、IAPP 和 Remote Files；
10. `disk_quotas.yml`：发布已初始化文件系统的配额策略。

在启用 `AccountingStorageEnforce` 前，必须确认 SlurmDBD、Account、用户和分区 Association 已完整建立。数据库和授权状态不完整时不要继续执行后续阶段。

## 完整站点收敛

`site.yml` 会连续修改多个子系统，只在变更窗口内由超级管理员执行：

```bash
ansible-playbook ansible/playbooks/site.yml --syntax-check
ansible-playbook ansible/playbooks/site.yml --check --diff
ansible-playbook ansible/playbooks/site.yml
```

通常优先使用单个工作包，便于审阅变更和定位故障。完整站点运行前确认仓库干净、Vault 可解锁、数据库可用，且控制节点和计算节点均能通过 Ansible 连接。

## 紧急恢复

如果 Association 强制导致正常用户无法提交，先从 `slurm.conf` 移除 `AccountingStorageEnforce`，再执行：

```bash
scontrol reconfigure
```

不要清空 SlurmDBD 数据库、删除 Association、删除 Slurm 状态目录或修改 NVIDIA 驱动。恢复提交后保留现场日志和配置差异，先修复清单或数据库状态，再重新启用强制。

## 超级管理员日常检查

```bash
scontrol ping
sinfo -N -l
scontrol show partition
squeue
sacctmgr ping
sshare --all --long
systemctl is-active mariadb slurmdbd slurmctld
systemctl is-active prometheus grafana-server apache2
```

详细的架构决策记录位于 `docs/superpowers/specs/`；它们用于解释设计取舍，不替代本页的操作顺序。
