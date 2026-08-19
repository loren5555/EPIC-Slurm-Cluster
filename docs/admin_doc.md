# Admin Doc（管理员）

> 面向日常运维（轻量化）：服务启停、健康检查、日志清理、账户管理指引位。

## 1) 组件概览
- Frontend：**Open OnDemand**
- Scheduler：**Slurm**（`slurmctld`、`slurmdbd`、`slurmrestd`）
- Metrics：exporters + **Prometheus** + **Grafana**
- 其它：反代/证书、SSH/BMC

> 当前策略： `/home` 限制20G；CPU 不排队、GPU 排队；内存无硬限。

## 2) 常用服务与启停（示例）

```bash
# OOD Web
sudo systemctl status apache2
sudo systemctl reload apache2

# Slurm
sudo systemctl status slurmctld
sudo systemctl status slurmdbd
sudo systemctl status slurmrestd
# restart:
sudo systemctl restart slurmctld slurmdbd

# Prometheus / Grafana
sudo systemctl status prometheus
sudo systemctl status grafana-server
```

## 3) 日志与排障

Slurm：`/var/log/slurm/*.log`（如 slurmctld.log、slurmdbd.log）

OOD：`/var/log/ondemand-nginx/`

Web：`/var/log/apache2/`

用户会话（Nginx per-user）：`/var/log/ondemand-nginx/<user>/*`

Prometheus / Grafana：根据安装路径查看 logs/

## 4) 存储与配额现状

/home：A100 本地 ext4，共688G；普通用户 soft 20GiB、hard 30GiB，宽限期3天。

/workspace：A100 本地 ext4，共14T RAID0 无备份，只放可再生/非关键数据；普通用户 soft 1TiB，不设 hard，宽限期7天。

/data：NFS，共28T 存放大型数据集与模型权重。

配额的文件系统初始化由管理员手工完成（`fstab`、remount、`quotacheck`、`quotaon`）；持续的用户限额和 OOD 首页配额展示由 Ansible `disk_quota` role 管理。该 role 不修改挂载参数，也不运行 `quotacheck`。

## 5) BMC 面板访问

通过堡垒机做本地转发：
```bash
ssh -N -L 8443:192.168.100.2:443 maintain@222.20.76.74
# 浏览器打开 https://localhost:8443 登录
```
账户与密码独立管理，不纳入普通用户账户体系。

## 6) 管理员权限与配置部署

管理员身份、职责和受限 sudo 命令由
`ansible/vars/administrators.yml` 与 `playbooks/administrators.yml` 管理。

- `epic-superadmins`：集群所有者及一名未来超管，拥有完整 `sudo`；
- `epic-operators`：7 位业务管理员，可拉取受保护的 `main`，运行指定
  Ansible 工作包，管理 Slurm 作业和节点状态；
- 业务管理员不拥有 root shell、任意 `sudo`、MariaDB 密码、Ansible Vault
  密码或任意 systemd 控制权限；
- 管理员名单中的用户必须已存在于 `ansible/vars/users.yml`。
- 从 `epic_operators` 删除用户后，再部署 `administrators.yml` 会同时撤销其
  受限 sudo 权限和 Slurm `AdminLevel=Operator`。

首次部署或修改管理员名单后，由现有 `administrator` 账户或超管执行：

```bash
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-playbook playbooks/administrators.yml --check
ansible-playbook playbooks/administrators.yml
```

新加入管理员需要重新登录 SSH，使其新的 Unix 组成员关系生效。业务管理员的
固定白名单 sudo 使用 `NOPASSWD`，因为普通集群账号没有 Linux 密码；这不授予
root shell 或任意 sudo 命令。

所有持久配置先通过 GitHub 提交并合并。控制节点部署目录由
`administrator` 持有，业务管理员不可在本机修改文件。合并后在控制节点执行：

```bash
sudo git -C /srv/epic/repos/EPIC-Slurm-Cluster status --short
sudo git -C /srv/epic/repos/EPIC-Slurm-Cluster pull --ff-only origin main

cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible

# 将 users.yml 替换为本次变更对应的固定工作包。
sudo env ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg \
  ansible-playbook /srv/epic/repos/EPIC-Slurm-Cluster/ansible/playbooks/users.yml --check

sudo env ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg \
  ansible-playbook /srv/epic/repos/EPIC-Slurm-Cluster/ansible/playbooks/users.yml
```

业务管理员可执行的工作包为 `users.yml`、`ssh_access.yml`、`slurm.yml`、
`slurm_associations.yml`、`disk_quotas.yml`、`monitoring.yml`、`grafana.yml`
和 `ood.yml`。`site.yml` 只由超管执行，因为它一次变更多个子系统。

所有集群用户的 Linux 密码保持锁定。OOD 使用独立密码；业务管理员可重置
已有用户的 OOD 密码：

```bash
sudo htpasswd /etc/ood/auth/htpasswd <username>
```

该命令只接受 `users.yml` 中已声明的用户名，并会交互式要求输入新密码。密码
哈希不进入 Git。管理员不得直接使用 `passwd`、`usermod`、`useradd`、`userdel`、
`gpasswd` 或 `sacctmgr` 修改持久用户、权限与账户策略。

统一在管理端执行用户创建、组分配、SSH Key 下发等。

[用户ID、组ID、统计账户表](id_table.md)

[《管理员新增用户说明》](https://infinity-frontier.notion.site/28c835def60d8020b05cf1c03a7aff2a)


## 7) 变更管理与公告

平台变更（停机维护/策略调整/数据迁移）提前通过群/公告发布。\
平台公告文件夹位置："/etc/ood/config/announcements.d/"其中的所有未读消息都会推送至平台主页。

文档与 Issues 同步更新关键变更点：存储调整、队列策略、IApp 行为变更等。

