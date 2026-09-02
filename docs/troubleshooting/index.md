---
layout: default
title: 故障手册
nav_order: 6
---

# 故障手册

本手册是用户、管理员和开发者的统一故障查询入口。先按现象查找；涉及密码、
私钥、Vault、MUNGE key 或数据库凭据时，不要将其写入 Issue 或日志附件。

<a id="user-troubleshooting"></a>

## 用户问题

<a id="job-pending"></a>

### 作业一直排队

```bash
squeue -u "$USER"
scontrol show job <job-id>
```

检查目标分区、等待原因、GPU 数量、CPU、内存和时限。资源不足时只能等待或
减少申请量，不要反复提交同一作业。

<a id="job-failed-immediately"></a>

### 作业立即失败

依次检查：

1. `cd` 的工作目录是否存在；
2. Python 或 Conda 环境路径是否正确；
3. 输入文件是否存在且可读；
4. 作业日志的最后一条错误；
5. `sacct -j <job-id> --format=JobID,State,ExitCode` 的结果。

<a id="interactive-app-unreachable"></a>

### Interactive App 无法连接

确认会话卡片中的作业仍在运行，再查看会话日志。常见原因是工作目录不存在、
请求超过主机上限，或计算节点缺少应用运行时。

在对应计算节点按实际应用检查可执行文件：

```bash
test -x /usr/local/bin/code-server
test -x /usr/bin/ttyd
test -x /opt/jupyterlab/bin/jupyter-lab
test -x /opt/tensorboard/bin/tensorboard
```

缺少哪个就只补哪个，安装方法见 [Other：手工软件准备](../other/02-manual-software-bootstrap.md)。
不要仅因一个 IAPP 缺失而将整个节点或 Slurm 下线。

<a id="gpu-not-visible"></a>

### GPU 不可见或数量不对

确认作业提交到 GPU 主机分区，并使用 `--gres=gpu:N` 或 OOD 的 GPU 字段申请。
在作业内运行：

```bash
echo "$CUDA_VISIBLE_DEVICES"
nvidia-smi -L
```

### 磁盘空间不足

```bash
df -h /home /workspace /data
quota -s
```

先清理缓存和可再生成的中间文件，将长期数据移到 `/data`。不要删除别人的目录或
绕过配额。

<a id="admin-troubleshooting"></a>

## 管理员问题

### 用户配置工作包失败

先保留失败 task 和目标主机，不要继续完整 `site.yml`。`user_onboarding.yml` 的顺序是：

```text
users.yml → ssh_access.yml → slurm_associations.yml → disk_quotas.yml → ood.yml
```

身份或 SSH 预检失败时，使用本页后面的 [UID/GID 冲突](#identity-uid-gid-conflict)
或 [SSH 缺少受管用户](#ssh-missing-managed-user)。

### 作业或分区异常

```bash
scontrol show job <job-id>
sacct -j <job-id> --format=JobID,User,Account,Partition,State,ExitCode,Elapsed,AllocTRES
sinfo -N -l
```

资源申请或脚本问题由管理员协助用户修正。节点 `DOWN`、`DRAIN`、`INVALID_REG`、
Slurm 服务或数据库问题转入下面的开发者排障。

### OOD 会话目录不可用

OOD 的会话目录依赖共享挂载。先在发生问题的主机检查 automount 和实际挂载：

```bash
systemctl status srv-epic-ood.automount --no-pager
mountpoint /srv/epic-ood
```

再在导出端检查 `exportfs -v`。只修复会话挂载，不要为了恢复 OOD 同时重启 Slurm、
SSH 或无关计算任务。恢复后实际启动一个 IAPP 即可验收。

<a id="developer-troubleshooting"></a>

## 开发者与部署问题

### SlurmDBD 或 MariaDB 无法连接

```bash
sacctmgr ping
systemctl status mariadb slurmdbd --no-pager
journalctl -u slurmdbd --since today
ss -lntp | grep -E ':(3306|6819)\b'
```

依次核对数据库服务、Vault 中的凭据、`/etc/slurm/slurmdbd.conf` 权限、MUNGE、主机
时间和 Slurm 主版本。不要通过清空数据库验证连接；修复后以 `sacctmgr ping` 和一条
真实作业的 `sacct` 记录验收。

### 启用记账后出现 Unknown TRES

检查 `slurm.conf` 是否声明 `AccountingStorageTRES=gres/gpu`，SlurmDBD 中是否已有当前
cluster 记录，以及 `slurmctld` 与 `slurmdbd` 是否为兼容的主版本：

```bash
scontrol show config | grep -E 'AccountingStorage(TRES|Type)'
sacctmgr show cluster
slurmctld -V
slurmdbd -V
```

先恢复 TRES 与版本一致性，再重载配置；不要删除既有记账数据。

### Prometheus target 或 exporter 下线

先在 Prometheus Targets 页面确认具体目标，再到该主机检查对应服务和最近日志：

```bash
systemctl --failed
systemctl status node_exporter nvitop-exporter nvidia-dcgm-exporter --no-pager
journalctl -u <service> --since today
```

只处理实际失败的服务。短时下线通知使用者、恢复后人工刷新页面确认即可，不增加自动
切换、无限重启或仅用于检查 dashboard 文本的测试。

<a id="node-state-failure"></a>

### 节点处于 DOWN、DRAIN 或 INVALID_REG

```bash
scontrol show node <node>
sinfo -N -l <node>
sudo journalctl -u slurmd --since today
```

确认节点通信、MUNGE、`slurmd`、时间同步和 host vars 资源声明。原因处理完后再恢复：

```bash
scontrol update nodename=<node> state=resume
```

<a id="association-enforcement-recovery"></a>

### Association 强制导致正常用户无法提交

先从 `slurm.conf` 移除 `AccountingStorageEnforce`，再执行：

```bash
scontrol reconfigure
```

不要清空 SlurmDBD 数据库、删除 Association 或 Slurm 状态目录。恢复提交后，
先修复清单或数据库状态，再重新启用强制。

<a id="identity-uid-gid-conflict"></a>

### Identity 预检报 UID/GID 冲突

`users.yml` 是集群数字身份的唯一权威来源。不要修改清单，而是将新节点单向校准。
`epic-cluster-compute-rtx4070-02` 遇到的映射为：

| 用户 | 节点现有 UID:主 GID | 清单要求 UID:主 GID |
|---|---:|---:|
| `yeyuanlin` | `1002:1003` | `10006:10006` |
| `yanghao` | `1004:1004` | `10010:10010` |
| `xiangxuxin` | `1001:1001` | `10011:10011` |

NFS 已断开。确认三个用户已退出新节点，然后在新节点执行：

```bash
sudo groupmod --gid 10006 yeyuanlin
sudo usermod --uid 10006 --gid 10006 yeyuanlin
sudo chown -R yeyuanlin:yeyuanlin /home/yeyuanlin

sudo groupmod --gid 10010 yanghao
sudo usermod --uid 10010 --gid 10010 yanghao
sudo chown -R yanghao:yanghao /home/yanghao

sudo groupmod --gid 10011 xiangxuxin
sudo usermod --uid 10011 --gid 10011 xiangxuxin
sudo chown -R xiangxuxin:xiangxuxin /home/xiangxuxin
```

返回控制节点重新收敛：

```bash
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
node=epic-cluster-compute-rtx4070-02

ansible-playbook playbooks/users.yml --limit "$node" --check --diff
ansible-playbook playbooks/users.yml --limit "$node"
ansible-playbook playbooks/users.yml --limit "$node" --check --diff
```

<a id="ssh-missing-managed-user"></a>

### SSH 预检报受管用户不存在

典型错误是 `SSH preflight failed for wangminlong`。所有集群用户必须先在每个计算节点上
拥有一致身份；`ssh_access` 只决定是否安装公钥。

```bash
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
node=epic-cluster-compute-rtx4070-02

ansible-playbook playbooks/users.yml --limit "$node"
ansible "$node" --become -m ansible.builtin.command -a "getent passwd wangminlong"

ansible-playbook playbooks/ssh_access.yml \
  --limit "controllers:$node" \
  --check --diff
ansible-playbook playbooks/ssh_access.yml \
  --limit "controllers:$node"
```

SSH 工作包的 limit 必须同时包含 `controllers` 和新节点，因为公钥来源在控制节点。

仍无法解决时，提交 Issue 并附上主机、分区、作业号、失败 task、复现步骤和必要日志。
