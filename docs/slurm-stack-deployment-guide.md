# EPIC 集群 Slurm、记账与监控部署说明

日期：2026-08-12  
状态：执行基线；各工作包按顺序实施

## 1. 文档用途

本文档定义 EPIC 实验室集群从当前可运行状态，逐步过渡到以下目标状态的完整顺序：

- Slurm 配置由 Ansible 统一生成和同步；
- 每台计算主机使用一个与完整主机名相同的 Slurm 分区；
- SlurmDBD 和 MariaDB 保存作业、用户及资源使用历史；
- Slurm Association 决定用户可以使用哪些主机；
- 普通 Fair Tree 根据组织和个人历史用量调整排队顺序；
- Prometheus 收集实时状态，Grafana 展示集群运行情况；
- Open OnDemand 后续直接选择具体主机分区，不依赖共享 Home。

本文档是执行顺序，不表示所有 Ansible 角色已经实现。只有当相应工作包的代码已经完成并经过 `--check --diff` 检查后，才运行该工作包的正式命令。

每次只执行一个工作包。一个工作包的验收条件全部满足后，再进入下一个工作包；遇到“停止条件”时不继续执行后续步骤。

## 2. 已确定的设计

### 2.1 当前主机

| 主机 | 管理类别 | Slurm 分区 | CPU | 可调度内存 | GPU |
|---|---|---|---:|---:|---|
| `epic-cluster-controller-01` | controller | 无 | - | - | 无 |
| `epic-cluster-compute-a100-01` | controlled | `epic-cluster-compute-a100-01` | 128 | 1024000 MiB | 8 × A100-SXM4-40GB |
| `epic-cluster-compute-rtx4070-01` | free | `epic-cluster-compute-rtx4070-01` | 32 | 126000 MiB | 1 × RTX 4070 Ti SUPER |

`controlled_compute_nodes` 和 `free_compute_nodes` 只是 Ansible 管理类别，不再生成同名 Slurm 分区。

### 2.2 主机分区

每台计算主机单独建立一个分区，分区名称使用完整主机名。这样做的原因是：

- 每台主机的 Home、软件环境和本地数据独立；
- 用户和 OOD 必须明确选择实际执行主机；
- 新增、停用或授权一台主机时，不影响同类别的其他主机；
- Grafana、`sacct` 和 `sreport` 能按真实主机分区统计。

所有主机分区初始均设置 `Default=NO`。命令行和 OOD 必须明确给出分区，避免作业落到没有对应环境或数据的主机。

### 2.3 controlled 与 free 的差异

controlled 主机使用 Slurm 做真实资源管控：

- 通过 cgroup 限制 CPU、内存和设备；
- GPU 只在 Slurm 分配或维护通道内可见；
- 作业必须申请所需 GPU；
- 排队顺序受 Fair-share 影响。

free 主机把 Slurm 作为统一提交和 OOD 入口：

- 保留普通 SSH 使用；
- 不设置用户额度、并发上限、抢占或强制 QoS；
- 通过 Slurm/OOD 启动的作业仍使用 cgroup 限制其申请到的 CPU、内存和 GPU；
- 直接通过 SSH 启动的进程不进入 Slurm 作业 cgroup，仍可自由使用主机资源；
- SSH 进程与 Slurm 作业可能互相争用资源，由实验室成员协调；
- Slurm 仍记录通过 Slurm 启动的作业，但无法统计普通 SSH 进程。

因此所有计算节点使用相同的 Slurm cgroup 约束。controlled 与 free 的差异来自 SSH/GPU 访问方式和调度政策，不来自 Slurm 作业内部的资源约束。

### 2.4 Linux 用户、Slurm Account 与 Association

三类对象承担不同职责：

| 对象 | 用途 | 示例 |
|---|---|---|
| Linux 私有组 | 本地文件所有权 | 用户 `liuhongbo` 的主组仍是 `liuhongbo` |
| Linux access group | 主机和目录等系统权限 | `EPIC-RL`、`CGCL`、`MLLMs` |
| Slurm Account | 组织层 Fair-share | `epic-rl`、`cgcl`、`mllms`、`cv3d`、`nue`、`individual` |
| Slurm user Association | 个人历史和分区使用权 | 用户、Account、集群、分区四元组 |

Linux 用户自己的同名主组必须保留。它是标准 Linux 文件权限模型的一部分，不应改造成 Slurm Account。

每个用户在 `users.yml` 中显式指定一个 `slurm_account`。没有组织归属的用户放入 `individual`，不从 Linux `groups` 数组隐式猜测，以免多组成员或临时访问产生歧义。

每个分区声明：

- `allowed_accounts`：批量允许某个组织；
- `allowed_users`：额外允许个别用户；
- `denied_users`：从已允许组织中排除个别用户。

最终授权用户集合按以下规则计算：

```text
(allowed_accounts 中的全部用户 + allowed_users) - denied_users
```

Ansible 为最终集合创建带分区名的用户 Association。不得为了方便给普通用户创建不带分区名的全局 Association，否则它可能绕过按主机划定的权限。

### 2.5 普通 Fair-share

本集群使用 Slurm 默认的 Fair Tree 算法，不使用 `FairShare=parent`：

- 每个用户的 `FairShare` 为 `1`；
- 每个组织 Account 的 shares 等于该 Account 当前有效用户数；
- 用户自己的历史用量主要影响本人；
- Account 的总用量仍会在一定程度上影响组内所有成员；
- 大组因为人数多而获得相应的 Account shares，避免仅因成员多而降低每个人的基础份额；
- 不设置硬额度、用量上限、抢占或强制 QoS。

历史使用量采用 7 天半衰期。作业等待时间也参与优先级，防止长期等待的作业一直排不到。

建议初始参数为：

```ini
# Prefer users with less recent usage while still rewarding queue age.
PriorityType=priority/multifactor
PriorityDecayHalfLife=7-0
PriorityCalcPeriod=5
PriorityMaxAge=7-0
PriorityWeightFairshare=10000
PriorityWeightAge=3000
PriorityWeightJobSize=0
PriorityWeightPartition=0
PriorityWeightQOS=0
```

Fair-share 只改变排队顺序，不会在用户达到某个用量后禁止提交或停止作业。

## 3. 目标服务关系与部署顺序

```text
users.yml + inventory + host_vars
                |
                v
             Ansible
                |
       +--------+---------+
       |                  |
       v                  v
Slurm configuration   SlurmDBD configuration
       |                  |
       v                  v
slurmctld/slurmd  --->  MariaDB
       |
       +---- Slurm OpenMetrics ----+
       |                           |
node_exporter / DCGM Exporter      v
       +----------------------> Prometheus ---> Grafana
```

固定顺序如下：

1. 记录并验证当前工作状态；
2. 用 Ansible 接管现有 Slurm 配置，并改为每主机一个分区；
3. 部署 MariaDB 和 SlurmDBD，但暂不改变提交权限；
4. 让 slurmctld 连接 SlurmDBD，只记录作业；
5. 创建 Account 和分区 Association，并生成授权审计表；
6. 开启 Association 强制和 Fair-share；
7. 部署 exporters 和 Prometheus；
8. 部署 Grafana 和仪表盘；
9. 最后再把 OOD 表单接到具体主机分区。

先记录、后强制是本方案最重要的保护措施。数据库、用户或分区 Association 未完整之前，不得启用 `AccountingStorageEnforce=associations`。

## 4. Ansible 文件组织

最终使用以下入口：

```text
ansible/
├── inventory/
│   ├── hosts.yml
│   ├── group_vars/all/
│   │   ├── slurm.yml
│   │   ├── slurm_accounting.yml
│   │   └── monitoring.yml
│   └── host_vars/
│       ├── epic-cluster-compute-a100-01.yml
│       └── epic-cluster-compute-rtx4070-01.yml
├── vars/
│   ├── users.yml
│   ├── slurm_accounts.yml
│   ├── slurm_partitions.yml
│   ├── secrets.example.yml
│   └── secrets.yml
├── playbooks/
│   ├── slurm.yml
│   ├── slurmdbd.yml
│   ├── slurm_associations.yml
│   ├── monitoring.yml
│   └── site.yml
└── roles/
    ├── slurm/
    ├── slurmdbd/
    ├── slurm_associations/
    ├── node_exporter/
    ├── dcgm_exporter/
    ├── prometheus/
    └── grafana/
```

`secrets.yml` 使用 Ansible Vault 加密。数据库密码不会提交为明文，但部署后的 `/etc/slurm/slurmdbd.conf` 必然包含数据库密码，因此文件权限必须是 `0600`，所有者为 `slurm:slurm`。

## 5. 工作包 0：固定当前基线

### 目的

在 Ansible 开始管理 Slurm 前，确认当前控制器、两个计算节点和已有测试作业均正常。此工作包不修改配置。

### 操作

在控制节点的项目目录执行：

```bash
# Confirm that Ansible can reach every managed host.
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible all -m ping

# Record the current Slurm service and resource state.
scontrol ping
sinfo -N -l
scontrol show partition
scontrol show nodes
squeue
```

分别在当前的 `free` 和 `controlled` 分区运行最小作业。A100 作业必须申请一张 GPU，并且作业内只能看到分配到的 GPU。工作包 1 完成后，这两个宽泛分区才会被完整主机名分区替代。

```bash
# Verify ordinary process execution on the RTX 4070 host.
srun \
  --partition=free \
  --nodes=1 \
  --ntasks=1 \
  hostname

# Verify controlled GPU allocation on the A100 host.
srun \
  --partition=controlled \
  --nodes=1 \
  --ntasks=1 \
  --gres=gpu:1 \
  nvidia-smi -L
```

### 预期结果

- Ansible 三台主机全部返回 `pong`；
- `scontrol ping` 显示主控制器为 `UP`；
- 两台计算节点为 `IDLE`、`MIXED` 或 `ALLOCATED`，没有非预期 `DOWN`/`DRAIN`；
- 两个最小作业成功结束；
- A100 作业只看到一张 GPU。

### 停止条件

任何节点不可达、MUNGE 失败、节点处于非预期状态，或当前测试作业失败时，先恢复当前系统，不进入工作包 1。

## 6. 工作包 1：Ansible 接管 Slurm 基础配置

### 目的

把当前可运行配置变成仓库中的声明式配置，同时完成每主机一个分区和统一的 Slurm 作业 cgroup 约束。此时仍不部署记账和权限强制。

### 配置变化

`slurm.conf` 的基础内容保持当前已经验证的设置，并作以下调整：

- `SlurmctldHost=epic-cluster-controller-01`，不固定控制器 IP；
- 节点记录只使用 `NodeName`，Slurm 通过各主机的 `/etc/hosts` 解析地址；
- inventory 中的 `ansible_host` 只负责 Ansible 的 SSH 连接，不写入 `slurm.conf`；
- 使用 Slurm 默认的 `6817` 和 `6818` 端口，不重复声明默认值；
- A100 和 RTX 4070 分别生成与主机同名的分区；
- 所有分区 `Default=NO`；
- 保留 `sched/backfill`、`select/cons_tres` 和 `CR_Core_Memory`；
- 暂不添加 `AccountingStorageType`、`AccountingStorageTRES` 或 `AccountingStorageEnforce`；
- 所有计算节点的 Slurm 作业均启用 CPU、内存和设备约束；
- free 节点的普通 SSH 进程不受这些 Slurm 作业 cgroup 约束；
- `slurm.conf` 只声明每台主机的通用 GPU 数量，例如 `Gres=gpu:8`；
- 计算节点的 `gres.conf` 使用 `AutoDetect=nvidia`，从本机驱动发现 GPU 型号和设备文件；
- 当前不配置 GPU 类型和 `Feature`，用户按主机分区选择硬件，并统一使用 `--gres=gpu:N` 申请 GPU。

### 操作

```bash
# Validate playbook and role syntax without contacting managed hosts.
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-playbook playbooks/slurm.yml --syntax-check

# Preview every generated configuration change without applying it.
ansible-playbook playbooks/slurm.yml --check --diff

# Apply the reviewed Slurm configuration.
ansible-playbook playbooks/slurm.yml

# Confirm that a second run is idempotent.
ansible-playbook playbooks/slurm.yml

# Inspect the two host-specific partitions after convergence.
scontrol show partition epic-cluster-compute-rtx4070-01
scontrol show partition epic-cluster-compute-a100-01

# Repeat the baseline workloads with their new explicit partition names.
srun \
  --partition=epic-cluster-compute-rtx4070-01 \
  --chdir=/tmp \
  --nodes=1 \
  --ntasks=1 \
  hostname

srun \
  --partition=epic-cluster-compute-a100-01 \
  --chdir=/tmp \
  --nodes=1 \
  --ntasks=1 \
  --gres=gpu:1 \
  nvidia-smi -L
```

### 预期结果

- 检查模式显示每台主机将获得正确的 `slurm.conf`、`cgroup.conf` 和本机 `gres.conf`；
- 正式运行后 `scontrol ping` 正常；
- `sinfo` 显示两个完整主机名分区；
- 第二次运行 `changed=0`；
- 工作包 0 的两类最小作业使用新的完整主机名分区后仍能成功运行；
- `scontrol show node` 显示 A100 注册 `gpu:8`、RTX 4070 注册 `gpu:1`；
- A100 单 GPU 作业只看到一张已分配的 GPU。

### 停止条件

- 生成了 `controlled`、`free` 之类的宽泛分区；
- 控制器地址被固定成某一个仅部分节点可达的 IP；
- A100 的普通 SSH 会话重新看到了 GPU；
- `slurmd -G` 报告自动发现的 GPU 数量或设备文件与节点实际硬件不匹配；
- 任何已有节点进入 `INVALID_REG`、`DOWN` 或非预期 `DRAIN`。

## 7. 工作包 2：部署 MariaDB 与 SlurmDBD

### 目的

先建立可靠的记账服务，但不改变用户当前提交权限。MariaDB 和 SlurmDBD 均部署在新控制节点；不依赖不可靠 NFS，也不在本阶段设计数据库热备。

### 配置原则

- MariaDB 和 SlurmDBD 软件包由管理员在控制节点手工安装；
- Ansible 只接管配置文件、数据库初始化和服务状态，不安装或升级系统软件包；
- SlurmDBD 使用当前 Slurm 25.11 系列软件源；
- 本工作包不同时升级 Slurm 大版本；
- MariaDB 只监听本机，SlurmDBD 通过本机数据库连接；
- SlurmDBD 使用现有 MUNGE；
- 数据库存放于控制节点本地标准路径；
- 数据库密码由 Ansible Vault 保存；
- SlurmDBD 配置和日志使用标准路径 `/etc/slurm/slurmdbd.conf`、`/var/log/slurm/slurmdbd.log`。

初始 MariaDB 参数采用适合实验室规模的保守值：

```ini
# Slurm accounting database settings.
[mysqld]
innodb_buffer_pool_size=4G
innodb_lock_wait_timeout=900
max_allowed_packet=16M
```

如果控制节点可用内存不足以长期给数据库保留 4 GiB，应在实现此工作包时按实机内存下调，而不是交换到磁盘。

`slurmdbd.conf` 的核心设置为：

```ini
# SlurmDBD identity and authentication.
AuthType=auth/munge
DbdHost=epic-cluster-controller-01
SlurmUser=slurm

# Local MariaDB storage.
StorageType=accounting_storage/mysql
StorageHost=localhost
StorageLoc=slurm_acct_db
StorageUser=slurm
StoragePass={{ slurmdbd_storage_password }}

# Standard runtime paths.
LogFile=/var/log/slurm/slurmdbd.log
PidFile=/run/slurmdbd/slurmdbd.pid
```

### 操作

#### 1. 确认软件来源并手工安装

先确认控制节点的软件源能够提供 MariaDB，并且 `slurmdbd` 候选版本属于当前使用的 Slurm 25.11 系列：

```bash
# Refresh package metadata without installing or upgrading packages.
sudo apt update

# Inspect the installed and candidate versions before changing the system.
apt-cache policy \
  mariadb-server \
  slurmdbd

# Preview dependencies, upgrades, and removals caused by the installation.
sudo apt-get \
  --simulate \
  install \
  mariadb-server \
  slurmdbd
```

预期 `slurmdbd` 的 Candidate 为 `25.11.x`。模拟结果可以安装新的 MariaDB 依赖和同一 Slurm 25.11 系列的软件包，但不能删除 `slurmctld`、MUNGE 或其他现有集群组件，也不能把 Slurm 切换到其他主版本。

确认模拟结果后再正式安装：

```bash
# Install only the accounting database and daemon selected above.
sudo apt install \
  mariadb-server \
  slurmdbd

# Confirm the installed daemon belongs to the current Slurm release series.
slurmdbd -V

# Record the exact installed package versions for troubleshooting.
dpkg-query -W \
  -f='${Package}\t${Version}\n' \
  mariadb-server \
  slurmdbd
```

预期 `slurmdbd -V` 输出 `25.11.x`。此时 MariaDB 通常已经启动；SlurmDBD 可能因为尚未生成 `/etc/slurm/slurmdbd.conf` 而没有启动，这部分由下一阶段的 Ansible 配置完成，不需要手工编辑配置文件。

#### 2. 建立加密数据库凭据

首先生成一个只包含十六进制字符的数据库密码。该命令只生成值，不会修改系统；把输出复制到下一步打开的 Vault 编辑器中：

```bash
# Generate a password that is safe in both MariaDB SQL and slurmdbd.conf.
openssl rand -hex 32
```

首次建立 Vault 文件时，根据 Ansible 提示设置 Vault 解锁密码。Vault 解锁密码用于以后运行 Ansible，不等于刚生成的数据库密码：

```bash
# Create the encrypted deployment secret file once.
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-vault create vars/secrets.yml
```

文件内容只需要保存数据库凭据。`slurmdbd_storage_password` 填写上一步生成的值：

```yaml
---
slurmdbd_storage_password: "replace-with-generated-password"
```

#### 3. 使用 Ansible 配置数据库和服务

Ansible 从这里开始只管理 MariaDB 参数、数据库和数据库用户、`slurmdbd.conf` 以及服务状态，不调用 APT 安装或升级软件包。按顺序检查和部署：

```bash
# Validate the playbook structure without changing the controller.
ansible-playbook playbooks/slurmdbd.yml \
  --syntax-check \
  --ask-vault-pass

# Preview configuration-file changes. Database initialization and live service
# checks are deliberately skipped in Ansible check mode.
ansible-playbook playbooks/slurmdbd.yml \
  --check \
  --diff \
  --ask-vault-pass

# Initialize the local database, install configuration files, and start both
# services. This does not modify packages, slurm.conf, or Slurm associations.
ansible-playbook playbooks/slurmdbd.yml \
  --ask-vault-pass

# A second run should find the same packages, files, database, and services.
ansible-playbook playbooks/slurmdbd.yml \
  --ask-vault-pass
```

### 预期结果

```bash
# Both services must be enabled and active.
systemctl is-enabled mariadb slurmdbd
systemctl is-active mariadb slurmdbd

# MariaDB must listen only on the controller loopback interface, while
# SlurmDBD exposes its authenticated protocol on the default port 6819.
sudo ss --listening --tcp --numeric --processes | grep -E ':3306|:6819'

# The local database and protected SlurmDBD configuration must exist.
sudo mariadb \
  --batch \
  --skip-column-names \
  --execute="SHOW DATABASES LIKE 'slurm_acct_db';"

sudo stat \
  --format='%U:%G %a %n' \
  /etc/slurm/slurmdbd.conf

# Confirm that the daemon uses the expected major release.
slurmdbd -V

# Installing the accounting service must not disturb the existing controller.
scontrol ping
```

预期结果：

- 第二次运行 playbook 时 `changed=0`；
- MariaDB 和 SlurmDBD 均为 `enabled`、`active`；
- MariaDB 的 `3306` 监听地址为 `127.0.0.1`，SlurmDBD 监听 `6819`；
- 数据库查询返回 `slurm_acct_db`；
- `/etc/slurm/slurmdbd.conf` 为 `slurm:slurm 600`；
- `slurmdbd -V` 为 `25.11.x`，日志中没有数据库权限、MUNGE 或表结构错误；
- `scontrol ping` 仍显示当前控制器为 `UP`。

此工作包尚未在 `slurm.conf` 中设置 `AccountingStorageType` 和 `AccountingStorageHost`，因此不在这里运行 `sacctmgr ping`。工包 3 连接 slurmctld 后，再通过 `sacctmgr ping` 验证完整的 Slurm 客户端到 SlurmDBD 链路。

### 停止条件

- APT 候选版本不是 Slurm `25.11.x`；
- APT 模拟安装会删除现有 Slurm、MUNGE 或其他集群组件；
- MariaDB 或 SlurmDBD 无法连续启动；
- SlurmDBD 与控制器不是同一个 Slurm 主版本；
- 数据库密码以明文进入未加密变量文件；
- MariaDB 出现在非 loopback 地址上；
- SlurmDBD 无法初始化数据库表或监听 `6819`；
- 当前 `scontrol ping` 或已有作业受到影响。

## 8. 工作包 3：开启作业记录，不强制权限

### 目的

让 slurmctld 开始把新作业写入 SlurmDBD，先验证数据链路。此阶段任何用户都不会因为缺少 Association 而被拒绝。

### 配置变化

Ansible 在公共 `slurm.conf` 中加入：

```ini
# Store job and step accounting through SlurmDBD.
AccountingStorageType=accounting_storage/slurmdbd
AccountingStorageHost=epic-cluster-controller-01
AccountingStorageTRES=gres/gpu,gres/gpu:a100-sxm4,gres/gpu:rtx4070
JobAcctGatherType=jobacct_gather/cgroup
JobAcctGatherFrequency=30
```

此时明确不设置 `AccountingStorageEnforce`。

在切换配置前，先确保集群记录存在：

```bash
# Inspect the existing cluster record first.
sacctmgr list cluster epic

# Run this only when the preceding output does not contain epic.
sacctmgr --immediate add cluster epic
```

实际 Ansible 任务必须做存在性检查，不能依靠命令失败实现幂等。

### 操作

```bash
# Preview the accounting client configuration.
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-playbook playbooks/slurm.yml --check --diff --ask-vault-pass

# Apply and reconfigure Slurm without restarting slurmctld.
ansible-playbook playbooks/slurm.yml --ask-vault-pass
```

随后在两个分区各运行一个带明确作业名的短作业，再查询记账结果：

```bash
# Submit one identifiable job to each partition.
srun \
  --job-name=accounting-rtx4070-test \
  --partition=epic-cluster-compute-rtx4070-01 \
  hostname

srun \
  --job-name=accounting-a100-test \
  --partition=epic-cluster-compute-a100-01 \
  --gres=gpu:1 \
  nvidia-smi -L

# Confirm that completed jobs reached SlurmDBD.
sacct \
  --starttime=today \
  --name=accounting-rtx4070-test,accounting-a100-test \
  --format=JobID,JobName,User,Account,Partition,State,Elapsed,AllocTRES
```

### 预期结果

- `scontrol reconfigure` 成功；
- 两个测试作业均可提交并完成；
- `sacct` 能看到作业、分区、状态、运行时间和 GPU TRES；
- SlurmDBD 短暂重启后，slurmctld 恢复传输记录；
- 未设置 Association 的用户仍可提交作业。

### 停止条件

- 日志出现 `slurmdbd is required`、认证失败或未知 TRES；
- `sacct` 长时间查不到已完成测试作业；
- 开启记账后用户意外收到 `Invalid account` 或 `Invalid user for account`；
- SlurmDBD 首次成功连接尚未完成就继续配置权限强制。

## 9. 工作包 4：建立 Account 与分区 Association

### 目的

在不启用强制的前提下，生成完整的组织、用户和主机授权关系，并把配置差异变成可审计的 Ansible 输出。

### 数据模型

`users.yml` 中每个用户增加一个明确字段：

```yaml
cluster_users:
  - name: liuhongbo
    uid: 10000
    gid: 10000
    slurm_account: epic-rl
```

`slurm_accounts.yml` 声明组织 Account。Account shares 由有效成员数生成，不手工重复维护：

```yaml
---
slurm_accounts:
  - name: epic-rl
    description: EPIC-RL members

  - name: cgcl
    description: CGCL members

  - name: mllms
    description: MLLMs members

  - name: cv3d
    description: CV3D members

  - name: nue
    description: NUE members

  - name: individual
    description: Users without an organization account
```

`slurm_partitions.yml` 显式声明主机授权。以下仅展示结构，实施前必须填入实际许可关系：

```yaml
---
slurm_partitions:
  - name: epic-cluster-compute-a100-01
    host: epic-cluster-compute-a100-01
    management_class: controlled
    allowed_accounts: []
    allowed_users: []
    denied_users: []

  - name: epic-cluster-compute-rtx4070-01
    host: epic-cluster-compute-rtx4070-01
    management_class: free
    allowed_accounts: []
    allowed_users: []
    denied_users: []
```

这里不把 `ssh_access` 自动转换成 Slurm 权限。SSH、Slurm 和 OOD 是三个不同入口，授权来源必须保持明确。

### Ansible 行为

Association 角色分为预检、计划、写入和审计四段：

1. 验证每个用户只有一个合法 `slurm_account`；
2. 验证所有分区名都对应 inventory 中的一台计算主机；
3. 计算 Account、用户和分区 Association 的新增、保留与移除集合；
4. 在 `--check` 中只显示计划，不写数据库；
5. 正式运行时创建或更新 Account 和 Association；
6. 输出最终授权矩阵和没有任何分区权限的用户；
7. 如果要移除的 Association 仍有运行或排队作业，任务必须失败，不自动删除。

删除 Association 会立即取消属于该 Association 的运行和排队作业，因此不得把删除操作隐藏在普通的同步过程里。

### 操作

```bash
# Preview every database association change.
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-playbook playbooks/slurm_associations.yml \
  --check \
  --diff \
  --ask-vault-pass

# Apply only after reviewing the complete user-by-partition matrix.
ansible-playbook playbooks/slurm_associations.yml \
  --ask-vault-pass

# Verify the resulting account tree and partition associations.
sacctmgr show account withassoc \
  format=Account,ParentName,Cluster,Partition,Fairshare

sacctmgr show user withassoc \
  format=User,DefaultAccount,Account,Cluster,Partition,Fairshare

sshare --all --long
```

### 预期结果

- 每个用户有一个默认 Slurm Account；
- 每个普通用户 Association 都带有具体分区名；
- Account shares 等于该 Account 的有效用户数；
- 用户 shares 均为 `1`；
- 审计表与管理员认可的主机权限一致；
- 仍未启用 `AccountingStorageEnforce`。

### 停止条件

- 任一用户没有默认 Account；
- 普通用户出现无分区的全局 Association；
- 授权矩阵中存在意外主机权限；
- 计划删除仍有作业的 Association；
- Account shares 与成员数不一致。

## 10. 工作包 5：启用 Association 强制与 Fair-share

### 目的

在授权矩阵已经完整验证后，让 Slurm 拒绝未获某主机权限的提交，并按照近期个人和组织用量调整队列顺序。

### 配置变化

在工作包 3 的记账配置基础上加入：

```ini
# Require a valid account and partition association.
AccountingStorageEnforce=associations

# Apply ordinary Fair Tree scheduling without hard quotas.
PriorityType=priority/multifactor
PriorityDecayHalfLife=7-0
PriorityCalcPeriod=5
PriorityMaxAge=7-0
PriorityWeightFairshare=10000
PriorityWeightAge=3000
PriorityWeightJobSize=0
PriorityWeightPartition=0
PriorityWeightQOS=0
```

不加入 `limits`、`qos` 或 `safe`，也不创建任何硬用量上限。

GPU 分区的初始计费以 GPU 时间为主，CPU 时间只占很小权重；CPU-only 主机按 CPU 时间计费。具体权重放在每台主机的 host vars 中，以便异构主机独立调整：

```yaml
# GPU host: one GPU-hour is the primary billing unit.
slurm_tres_billing_weights:
  cpu: 0.01
  gres/gpu: 1
```

未来新增纯 CPU 服务器时使用：

```yaml
# CPU host: one allocated CPU-hour is one billing unit.
slurm_tres_billing_weights:
  cpu: 1
```

### 操作

先选择一个有权限测试用户和一个无权限测试用户。不要使用 `root` 或 Slurm 管理员做拒绝测试。

```bash
# Preview the enforcement and priority configuration.
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-playbook playbooks/slurm.yml --check --diff --ask-vault-pass

# Apply the reviewed policy.
ansible-playbook playbooks/slurm.yml --ask-vault-pass

# Inspect the active priority weights.
sprio --weights
sshare --all --long
```

然后分别验证：

- 有权限用户能在对应主机分区提交；
- 无权限用户在该分区被提交阶段拒绝；
- 同一用户在另一获授权分区仍可提交；
- 两名均有权限用户的 `sshare` 原始用量和 Fair-share 值可以分别变化；
- 同一 Account 的总用量会反映到其成员的层级上；
- 等待时间能提高待运行作业的 age factor。

### 预期结果

- 权限按主机分区生效；
- 没有硬额度或运行时长限制；
- free 主机的普通 SSH 行为不改变；
- `sprio` 显示 Fair-share 权重为 10000、Age 权重为 3000；
- `sacct`、`sshare`、`sprio` 能解释作业记录和排队顺序。

### 停止条件

- 已授权用户被拒绝；
- 未授权用户可以提交；
- 任一用户所有分区权限意外消失；
- 配置中出现未经设计的 QOS、额度、抢占或并发限制；
- free 主机普通 SSH 使用受到 Slurm cgroup 影响。

若必须紧急恢复提交，先从 `slurm.conf` 移除 `AccountingStorageEnforce` 并执行 `scontrol reconfigure`。不要清空数据库或删除 Association。

## 11. 工作包 6：部署 Prometheus 与采集端

### 目的

建立实时监控链路。Prometheus 运行在控制节点，采集操作系统、GPU 和 Slurm 调度器指标。

### 指标来源

| 来源 | 部署位置 | 内容 | 默认端口 |
|---|---|---|---:|
| node_exporter | 全部主机 | CPU、内存、磁盘、网络、systemd | 9100 |
| NVIDIA DCGM Exporter | GPU 计算节点 | GPU 利用率、显存、温度、功耗、错误 | 9400 |
| Slurm 25.11 OpenMetrics | slurmctld | 作业、节点、分区、调度周期 | 6817 |
| accounting report collector | 控制节点 | 从 `sreport`/`sacct` 生成低频汇总 | node_exporter textfile |

不让 Grafana 直接查询 SlurmDBD 的内部表。Slurm 数据库结构属于 Slurm 实现细节，历史报表通过 `sacct`、`sreport` 或后续的低频汇总采集器读取。

### Slurm 指标配置

Slurm 25.11 已内置 OpenMetrics 插件，因此不再部署第三方 Slurm exporter：

```ini
# Expose Slurm metrics inside the laboratory network.
MetricsType=metrics/openmetrics
MetricsParameters=ignore_private_data
```

Prometheus 每 60 秒采集以下有界端点：

- `/metrics/jobs`
- `/metrics/nodes`
- `/metrics/partitions`
- `/metrics/scheduler`

初始阶段不采集 `/metrics/jobs-users-accts`。该端点会按用户和 Account 创建时间序列，长期维护时容易产生高基数；个人历史报表由 SlurmDBD 提供。

### GPU 采集说明

DCGM Exporter 作为 systemd 服务运行在 `system.slice`，因此 A100 节点即使对普通 SSH 会话隐藏 GPU，采集服务仍能看到设备。优先使用 NVIDIA 软件源提供的 `datacenter-gpu-manager-exporter` 包，并保证 exporter 与 DCGM 版本匹配。

### 操作

```bash
# Preview exporters, Prometheus targets, and Slurm metrics changes.
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-playbook playbooks/monitoring.yml \
  --check \
  --diff \
  --tags=exporters,prometheus

# Deploy exporters first, then the central Prometheus service.
ansible-playbook playbooks/monitoring.yml \
  --tags=exporters,prometheus
```

### 预期结果

```bash
# Verify the local operating-system exporter on each host.
curl --fail http://localhost:9100/metrics

# Verify the GPU exporter from system.slice on each GPU host.
curl --fail http://localhost:9400/metrics

# Verify Slurm's bounded OpenMetrics endpoints on the controller.
curl --fail http://localhost:6817/metrics/jobs
curl --fail http://localhost:6817/metrics/nodes
curl --fail http://localhost:6817/metrics/partitions
curl --fail http://localhost:6817/metrics/scheduler
```

Prometheus 的 Targets 页面中所有预期目标为 `UP`，且主机、GPU、作业、分区和调度指标都能查询。

### 停止条件

- DCGM Exporter 启动影响 NVIDIA 驱动、Fabric Manager 或现有 GPU 作业；
- A100 exporter 在 `user.slice` 中启动而看不到 GPU；
- Prometheus 高频请求导致 slurmctld 调度周期明显变长；
- 监控任务修改了 GPU 可见性或 Slurm 作业约束；
- Prometheus 目标使用临时 IP，而不是 inventory 生成的当前地址。

## 12. 工作包 7：部署 Grafana 与基础仪表盘

### 目的

为管理员和实验室成员提供低维护的可视化入口。Grafana 运行在控制节点，通过 provisioning 文件由 Ansible 管理。

### 初始仪表盘

只部署能稳定维护的四类仪表盘：

1. 集群概览：节点状态、队列长度、运行/等待作业；
2. 主机详情：CPU、内存、磁盘和网络；
3. GPU 详情：利用率、显存、温度、功耗和健康状态；
4. Slurm 调度：分区作业、调度周期和 backfill 状态。

用户和 Account 的长期使用量以 SlurmDBD 为准。第一阶段先提供经过验证的 `sreport` 管理报表；只有明确需要在 Grafana 中展示后，再增加低频汇总采集器，不让 Grafana 直接依赖 MariaDB 内部表。

### 操作

Grafana 使用官方稳定 APT 仓库，由 Ansible 管理软件源、数据源和仪表盘：

```bash
# Preview Grafana installation and provisioned dashboards.
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-playbook playbooks/monitoring.yml \
  --check \
  --diff \
  --tags=grafana

# Install Grafana and provision the Prometheus data source.
ansible-playbook playbooks/monitoring.yml \
  --tags=grafana
```

### 预期结果

- Grafana 服务启用并运行；
- Prometheus 数据源由文件自动创建，不需要网页中手工重复配置；
- 四类基础仪表盘均能加载数据；
- 重新运行 playbook 不会覆盖管理员未纳入 Ansible 的独立实验仪表盘；
- OOD 的 Grafana 链接后续只需指向该固定服务地址。

### 停止条件

- 仪表盘依赖未固定版本或无人维护的第三方 exporter；
- Grafana 直接读写 SlurmDBD 内部表；
- 监控部署改变 Slurm 调度或现有作业；
- 仪表盘无数据却继续部署 OOD 链接。

## 13. 工作包 8：接入 OOD

OOD 不属于本轮 Slurm 基础部署，在前七个工作包稳定后单独实施。届时：

- OOD 使用独立登录密码，不复用 Linux SSH 密码；
- OOD 表单显示友好主机名称，提交值使用完整分区名；
- IAPP 作业上下文使用控制节点提供的专用共享目录；
- 各计算主机 Home 和本地存储仍保持独立；
- 可选 NFS 只作为附加网络路径，掉线不能阻塞登录、Slurm、Home 或本地作业；
- 旧控制节点只作为备用 `slurmctld` 和紧急命令行入口，不运行 OOD。

### NUMA 与 GPU 亲和性开关

OOD IAPP 表单后续增加一个默认关闭的“NUMA/GPU 亲和优化”开关。这个开关只影响当前 IAPP 作业的资源绑定参数，不改变分区、默认内存或 cgroup 策略。

关闭时，IAPP 只按用户填写的 CPU、内存和 GPU 数量提交作业。开启时，提交模板附加以下 Slurm 参数：

```text
--sockets-per-node=1
--cpu-bind=cores
--mem-bind=local
--gres-flags=enforce-binding
```

开启后的目标是让 CPU 核心集中在一个 socket，将进程绑定到已分配核心，优先使用对应 NUMA 节点的本地内存，并要求 CPU 与所分配 GPU 的 socket 亲和关系一致。该选项适合 A100 上的单 socket、GPU 密集或 CPU/GPU 通信密集任务。

如果用户申请的 CPU、内存或 GPU 超过单个 socket 能提供的范围，OOD 不应生成上述绑定参数，并应提示用户关闭该选项或减少资源请求。普通任务默认保持关闭，避免因为亲和性要求导致本来可运行的作业长期等待。

## 14. 新增计算节点流程

新增服务器不修改模板逻辑，只增加数据并按既定顺序收敛：

1. 手工安装兼容的 Slurm 25.11、MUNGE、驱动和主机环境；
2. 同步 `administrator`、`slurm` 和集群用户 UID/GID；
3. 在 inventory 中加入完整主机名和当前可达地址；
4. 放入 `controlled_compute_nodes` 或 `free_compute_nodes`；
5. 在 host vars 中记录 CPU 拓扑、可调度内存、GPU、管理类别和计费权重；
6. 在 `slurm_partitions.yml` 增加同名分区及授权；
7. 先运行用户、SSH 和 Slurm playbook 的检查模式；
8. 正式同步身份和基础 Slurm 配置；
9. 在未强制授权前创建该分区 Association；
10. 运行 CPU/GPU 最小作业；
11. 加入 node_exporter、DCGM Exporter 和 Prometheus targets；
12. 最后在 OOD 中开放该主机入口。

新节点上线的验收标准是：身份一致、Slurm 注册正确、授权矩阵正确、最小作业成功、监控目标为 `UP`。IP 改变时只更新 inventory 的 `ansible_host` 并重新运行相关 playbook。

## 15. 日常权限调整

### 增加主机权限

1. 修改 `slurm_partitions.yml` 的 `allowed_accounts` 或 `allowed_users`；
2. 运行 Association playbook 的 `--check --diff`；
3. 确认只出现预期新增；
4. 正式应用；
5. 使用目标用户验证提交。

### 收回主机权限

1. 在 `denied_users` 增加用户，或从允许项中移除；
2. 检查该用户在该分区的运行和排队作业；
3. 有作业时先由管理员决定等待、通知或取消；
4. Association playbook 在作业仍存在时必须拒绝删除；
5. 作业清空后再次正式应用；
6. 验证该用户提交被拒绝，其他分区不受影响。

free 主机的临时协调仍可通过公告和管理员操作处理，不为临时情况增加 QOS、Reservation 或复杂策略。确实需要长期专用的设备再单独设计。

## 16. 运行报表与故障边界

### SlurmDBD 报表

```bash
# Review jobs completed since midnight.
sacct \
  --starttime=today \
  --format=JobID,User,Account,Partition,State,Elapsed,AllocTRES

# Review account and user utilization for the current month.
sreport cluster AccountUtilizationByUser start=month

# Explain current fair-share state.
sshare --all --long

# Explain the priority components of pending jobs.
sprio
```

### 故障边界

- SlurmDBD 短时不可用：slurmctld 在首次成功连接后可使用本地缓存；优先恢复数据库，不清空状态目录；
- Prometheus 不可用：只影响监控，不影响 Slurm 和作业提交；
- Grafana 不可用：只影响展示，不影响 Prometheus 和 Slurm；
- 可选 NFS 不可用：不得影响控制器、Home、本地作业或记账；
- 控制节点故障：旧控制节点的备用控制器方案另行实施，不与数据库共享不可靠 NFS；
- free 主机 SSH 负载过高：属于实验室协调问题，不视为 Slurm 资源隔离故障。

## 17. 整体完成标准

只有以下条件全部满足，才认为本轮 Slurm 栈部署完成：

- Ansible 再次运行为幂等；
- 每台计算主机有且只有一个同名分区；
- controlled/free 只作为 Ansible 管理类别；
- controlled 节点资源隔离有效，free 节点 SSH 使用不受限制；
- 所有用户具有明确的 Slurm Account；
- 所有普通用户 Association 都绑定具体分区；
- 授权和拒绝测试符合声明文件；
- `sacct`、`sreport`、`sshare` 和 `sprio` 输出正常；
- Fair-share 同时体现个人近期用量和组织层用量；
- 没有硬额度、强制 QOS、抢占或无意的并发限制；
- Prometheus 所有预期 targets 为 `UP`；
- Grafana 四类基础仪表盘有数据；
- SlurmDBD、Prometheus、Grafana 任一单独停止时，不会导致本地 Home、普通 SSH 或已经运行的本地进程失效。

## 18. 参考资料

- [Slurm Accounting and Resource Limits](https://slurm.schedmd.com/accounting.html)
- [Slurm Resource Limits and Associations](https://slurm.schedmd.com/resource_limits.html)
- [Slurm Multifactor Priority](https://slurm.schedmd.com/priority_multifactor.html)
- [Slurm Fair Tree](https://slurm.schedmd.com/fair_tree.html)
- [Slurm 25.11 Metrics Guide](https://slurm.schedmd.com/metrics.html)
- [NVIDIA DCGM Exporter Installation](https://docs.nvidia.com/datacenter/dcgm/latest/installation/install-dcgm-exporter.html)
- [Grafana Installation on Debian or Ubuntu](https://grafana.com/docs/grafana/latest/setup-grafana/installation/debian/)
