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

### 2.5 普通 Fair-share 与 NUE 并发限制

本集群使用 Slurm 默认的 Fair Tree 算法，不使用 `FairShare=parent`：

- 每个用户的 `FairShare` 为 `1`；
- 每个组织 Account 的 shares 等于该 Account 当前有效用户数；
- 用户自己的历史用量主要影响本人；
- Account 的总用量仍会在一定程度上影响组内所有成员；
- 大组因为人数多而获得相应的 Account shares，避免仅因成员多而降低每个人的基础份额；
- 不设置累计用量额度或抢占；唯一的初始并发限制是 `nue` Account
  在整个集群中合计最多同时使用 2 张 GPU；
- Job QoS 只用于排队优先级。它不承载资源限制，也不允许抢占运行中的作业。

历史使用量采用 14 天半衰期。作业等待时间在 7 天达到最大值，防止长期等待
的作业一直排不到。

建议初始参数为：

```ini
# Prefer users with less recent usage while still rewarding queue age.
PriorityType=priority/multifactor
PriorityDecayHalfLife=14-0
PriorityCalcPeriod=5
PriorityMaxAge=7-0
PriorityWeightFairshare=10000
PriorityWeightAge=3000
PriorityWeightJobSize=0
PriorityWeightPartition=0
PriorityWeightQOS=30000
```

Fair-share 和 Job QoS 只改变排队顺序，不会在用户达到某个历史用量后禁止
提交，也不会抢占或停止已经运行的作业。

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
AccountingStorageTRES=gres/gpu
JobAcctGatherType=jobacct_gather/cgroup
JobAcctGatherFrequency=30
```

此时明确不设置 `AccountingStorageEnforce`。CPU、内存、节点等基础 TRES 默认记录；这里只追加通用 `gres/gpu`，与当前所有节点使用 `Gres=gpu:N` 的无类型配置保持一致。GPU 型号仍可通过分区名称区分，不创建已经取消的 typed GRES。

Ansible 按以下顺序处理集群记录：

1. 先把包含 SlurmDBD 地址的新 `slurm.conf` 写到所有主机；
2. 在重新加载 `slurmctld` 前，控制节点使用 `sacctmgr` 查询已有 Cluster；
3. 仅当 `epic` 不存在时创建 Cluster 记录；
4. Cluster 已存在时不执行写操作；
5. 最后运行 `scontrol reconfigure`，让所有 Slurm daemon 重新读取配置。

本工作包只创建 Cluster 记录，不创建 Account、用户 Association 或 QoS。

### 操作

```bash
# Validate the playbook structure without changing any host.
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-playbook playbooks/slurm.yml --syntax-check

# Preview the shared accounting client configuration.
ansible-playbook playbooks/slurm.yml --check --diff

# Apply the configuration and ask all Slurm daemons to reread it without a
# process restart.
ansible-playbook playbooks/slurm.yml

# Confirm that the same declaration produces no further changes.
ansible-playbook playbooks/slurm.yml

# Verify the authenticated Slurm client-to-SlurmDBD path and cluster record.
sacctmgr ping
sacctmgr list cluster epic

# Confirm that accounting is enabled without association enforcement.
scontrol show config | grep -E \
  'AccountingStorage(Type|Host|TRES|Enforce)|JobAcctGather(Type|Frequency)'
```

随后在两个分区各运行一个带明确作业名的短作业，再查询记账结果：

```bash
# Submit one identifiable job to each partition.
srun \
  --job-name=accounting-rtx4070-test \
  --partition=epic-cluster-compute-rtx4070-01 \
  --chdir=/tmp \
  --nodes=1 \
  --ntasks=1 \
  hostname

srun \
  --job-name=accounting-a100-test \
  --partition=epic-cluster-compute-a100-01 \
  --chdir=/tmp \
  --nodes=1 \
  --ntasks=1 \
  --gres=gpu:1 \
  nvidia-smi -L

# Confirm that completed jobs reached SlurmDBD.
sacct \
  --starttime=today \
  --name=accounting-rtx4070-test,accounting-a100-test \
  --format=JobID,JobName,User,Account,Partition,State,Elapsed,AllocTRES
```

### 预期结果

- 第二次运行 playbook 时 `changed=0`；
- `scontrol reconfigure` 成功；
- `slurmctld` 和 `slurmd` 不因本次 `slurm.conf` 变化而重启；
- `sacctmgr ping` 显示 SlurmDBD 为 `UP`，Cluster 列表包含 `epic`；
- `scontrol show config` 显示通用 `gres/gpu` 记账，`AccountingStorageEnforce` 保持未设置或 `none`；
- 两个测试作业均可提交并完成；
- `sacct` 能看到作业、分区、状态、运行时间和 GPU TRES；
- SlurmDBD 短暂重启后，slurmctld 恢复传输记录；
- 未设置 Association 的用户仍可提交作业。

### 停止条件

- 日志出现 `slurmdbd is required`、认证失败或未知 TRES；
- 配置中重新出现已经取消的 typed GPU TRES；
- 未进入工包 4 就出现 `AccountingStorageEnforce`；
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
    # All concurrent NUE jobs may use at most two GPUs in total.
    group_tres: gres/gpu=2

  - name: individual
    description: Users without an organization account
```

`slurm_partitions.yml` 只声明主机授权：

```yaml
---
slurm_partitions:
  - name: epic-cluster-compute-a100-01
    host: epic-cluster-compute-a100-01
    management_class: controlled
    allowed_accounts:
      - epic-rl
      - cgcl
      - mllms
      - cv3d
      - nue
      - individual
    allowed_users: []
    denied_users: []

  - name: epic-cluster-compute-rtx4070-01
    host: epic-cluster-compute-rtx4070-01
    management_class: free
    allowed_accounts: []
    allowed_users:
      - liuhongbo
      - huodongkun
    denied_users: []
```

这里不把 `ssh_access` 自动转换成 Slurm 权限。SSH、Slurm 和 OOD 是三个不同入口，授权来源必须保持明确。

`nue` 的 `GrpTRES=gres/gpu=2` 设置在集群级 Account Association 上，表示该组
在所有获授权分区中的运行作业合计最多占用 2 张 GPU。目前 NUE 只获准使用
A100 主机，因此实际效果仍是最多同时使用 2 张 A100。以后若授予 NUE 其他
GPU 主机权限，这个限制会跨这些主机合并计算。达到上限后，新作业继续排队，
不会被拒绝、终止或抢占。该限制在本工作包只写入 SlurmDBD；工作包 5 开启
Association limits 后才实际参与调度。

### Ansible 行为

Association 角色分为预检、计划、写入和审计四段：

1. 验证每个用户只有一个合法 `slurm_account`；
2. 验证所有分区名都对应 inventory 中的一台计算主机；
3. 计算集群级 Account Association 和分区级用户 Association 的差异；
4. 在 `--check` 中只显示计划，不写数据库；
5. 正式运行时创建或更新 Account 和 Association；
6. 输出最终授权矩阵和没有任何分区权限的用户；
7. 如果要移除的 Association 仍有运行或排队作业，任务必须失败，不自动删除。

删除 Association 会立即取消属于该 Association 的运行和排队作业，因此不得把删除操作隐藏在普通的同步过程里。
角色会把两个已声明分区内的用户权限收敛为准确矩阵，包括清理已经从
`users.yml` 移除的旧用户 Association。已经产生历史记录的 Account 实体本身
不自动删除；无用户的旧 Account 保留仅用于 `sacct`/`sreport` 历史查询，不再
获得已声明分区的使用权限。

### 操作

```bash
# Preview every database association change.
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-playbook playbooks/slurm_associations.yml \
  --check \
  --diff

# Apply only after reviewing the complete user-by-partition matrix.
ansible-playbook playbooks/slurm_associations.yml

# Confirm that a second run is idempotent.
ansible-playbook playbooks/slurm_associations.yml

# Verify the resulting account tree and partition associations.
sacctmgr show account withassoc \
  format=Account,ParentName,Cluster,Partition,Fairshare,GrpTRES

sacctmgr show user withassoc \
  format=User,DefaultAccount,Account,Cluster,Partition,Fairshare

sshare --all --long
```

### 预期结果

- 每个用户有一个默认 Slurm Account；
- 每个普通用户 Association 都带有具体分区名；
- Account shares 等于该 Account 的有效用户数；
- 用户 shares 均为 `1`；
- RTX 4070 分区只有 `allowed_users` 中声明用户的 Association；
- A100 分区包含全部声明用户；
- `nue` 的集群级 Account Association 显示 `GrpTRES=gres/gpu=2`；
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
# Enforce valid Associations and their declared concurrent-resource limits.
# The limits option automatically includes association enforcement.
AccountingStorageEnforce=limits,qos

# Apply ordinary Fair Tree scheduling without hard quotas.
PriorityType=priority/multifactor
PriorityDecayHalfLife=14-0
PriorityCalcPeriod=5
PriorityMaxAge=7-0
PriorityWeightFairshare=10000
PriorityWeightAge=3000
PriorityWeightJobSize=0
PriorityWeightPartition=0
PriorityWeightQOS=30000

# Running jobs must never be preempted by another job or QoS.
PreemptType=preempt/none
PreemptMode=OFF
```

`limits` 用于执行 Association 以及 `nue` 的集群级并发 2 卡上限；它不会限制
其他 Account，也不会在用量达到某个历史累计值后停止作业。

工作包 5 同时建立两个 Job QoS：普通作业使用 `normal`，管理员可以把
`project` 的使用权临时授予指定用户。获授权用户可在 OOD 的 Additional
Arguments 中加入 `--qos=project`，获得更高的排队优先级。两个 QoS 均不设置
GPU 数量、运行时长或累计用量限制，也不配置任何抢占关系。具体 QoS
Association 由工作包 5 的 Ansible 配置统一维护。

`project` 的 QoS Priority 为 100。在当前 Fair-share 最大 10000、Age 最大
3000 的配置下，QoS Weight 30000 使 `project` 形成独立的最高优先级区间，
而不是普通加分。未来如需较弱的人工提升，可在 10～20 范围增加
`promoted` 类 QoS；本工作包暂不创建这些 QoS。

GPU 分区的初始计费以 GPU 时间为主，CPU 时间只占很小权重；CPU-only 主机按 CPU 时间计费。具体权重放在每台主机的 host vars 中，以便异构主机独立调整：

```yaml
# GPU host: one GPU-hour is the primary billing unit.
slurm_tres_billing_weights: "CPU=0.01,GRES/gpu=1"
```

未来新增纯 CPU 服务器时使用：

```yaml
# CPU host: one allocated CPU-hour is one billing unit.
slurm_tres_billing_weights: "CPU=1"
```

### 操作

先选择一个有权限测试用户和一个无权限测试用户。不要使用 `root` 或 Slurm
管理员做拒绝测试。下面分两阶段部署，先建立 QoS 与用户许可，再开启强制。

```bash
# Stage 1: preview the Job QoS and per-user Association changes.
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-playbook playbooks/slurm_associations.yml --check --diff

# Create normal/project and assign the allowed QoS to each Association.
ansible-playbook playbooks/slurm_associations.yml

# A second run must report changed=0.
ansible-playbook playbooks/slurm_associations.yml
```

第一阶段的预期结果是：`normal` 与 `project` 均存在，`project` 的 Priority 为
100；所有分区 User Association 的 DefaultQOS 为 `normal`；只有
`project_qos_users` 中的用户同时拥有 `normal,project`。以下命令使用
`--parsable2`，不会截断较长的用户名或分区名：

角色会读取 QoS 的全部资源、作业数和时长限制字段。若旧 QoS 带有任何未声明
限制、Flag 或抢占关系，Ansible 会在写入前停止并显示原始记录，不会自动猜测
哪些旧策略应当删除。

```bash
# Inspect Job QoS. Preempt and GrpTRES must remain empty.
sacctmgr \
  --noheader \
  --parsable2 \
  show qos \
  where Name=normal,project \
  format=Name,Priority,Preempt,GrpTRES |
column --table --separator='|'

# Inspect direct Association values instead of inherited values.
sacctmgr \
  --noheader \
  --parsable2 \
  show association \
  WOPLimits \
  where Cluster=epic \
  format=Account,User,Partition,Fairshare,QOS,DefaultQOS,GrpTRES |
column --table --separator='|'
```

确认第一阶段正确后再开启提交强制和 Fair-share：

```bash
# Stage 2: preview the controller policy and partition billing weights.
ansible-playbook playbooks/slurm.yml --check --diff

# Reconfigure Slurm with Association enforcement and multifactor priority.
ansible-playbook playbooks/slurm.yml

# A second run must report changed=0.
ansible-playbook playbooks/slurm.yml

# Inspect the active priority weights.
sprio --weights
sshare --all --long

# Confirm the active enforcement, priority, and preemption settings.
scontrol show config |
grep -E 'AccountingStorageEnforce|Priority(Type|Weight|Decay|Calc|MaxAge)|Preempt'
```

然后分别验证：

- 有权限用户能在对应主机分区提交；
- 无权限用户在该分区被提交阶段拒绝；
- 同一用户在另一获授权分区仍可提交；
- 两名均有权限用户的 `sshare` 原始用量和 Fair-share 值可以分别变化；
- 同一 Account 的总用量会反映到其成员的层级上；
- `nue` 的运行中作业跨全部获授权分区合计申请 2 张 GPU 后，新增 GPU 作业以
  `AssocGrpGRES` 或对应 Association limit 原因等待；
- 等待时间能提高待运行作业的 age factor。
- 获得 `project` 权限的用户可以通过 `--qos=project` 提高排队优先级；
- `project` 作业不会抢占任何已经运行的作业。

### 预期结果

- 权限按主机分区生效；
- 除 `nue` 的集群级并发 2 卡上限外，没有累计额度或运行时长限制；
- free 主机的普通 SSH 行为不改变；
- `sprio` 显示 Fair-share 权重为 10000、Age 权重为 3000、QoS 权重为
  30000；
- `sacct`、`sshare`、`sprio` 能解释作业记录和排队顺序。

### 停止条件

- 已授权用户被拒绝；
- 未授权用户可以提交；
- 任一用户所有分区权限意外消失；
- 配置中出现除 `normal`、`project` 以外的 QoS，或出现累计额度、抢占及其他
  未经设计的并发限制；
- free 主机普通 SSH 使用受到 Slurm cgroup 影响。

若必须紧急恢复提交，先从 `slurm.conf` 移除 `AccountingStorageEnforce` 并执行 `scontrol reconfigure`。不要清空数据库或删除 Association。

## 11. 工作包 6：部署 Prometheus 与采集端

### 目的

建立实时监控链路。Prometheus 在控制节点的本地系统盘保存最多 180 天数据；监控服务不成为 Slurm、SSH、驱动或作业的依赖。

软件安装由管理员手工完成，Ansible 只管理配置和 systemd 服务。这样不会因为各主机 Ubuntu、内核和 NVIDIA 软件栈不同而触发不可控的软件升级。

### 最终组件与频率

| 来源 | 主机 | 内容 | 端口 | 周期 |
|---|---|---|---:|---:|
| node_exporter | 全部主机 | CPU、内存、磁盘、网络、systemd | 9100 | 10 秒 |
| NVIDIA DCGM Exporter | GPU 节点 | GPU 健康、利用率、显存、温度、功耗和错误 | 9400 | 10 秒 |
| nvitop-exporter | GPU 节点 | GPU 进程、用户、PID、命令和进程用量 | 5050 | 10 秒 |
| Slurm 25.11 OpenMetrics | 控制节点 | 作业、节点和分区 | 6817 | 2 分钟 |
| Slurm 25.11 OpenMetrics | 控制节点 | 调度周期 | 6817 | 5 分钟 |
| EPIC Slurm usage collector | 控制节点 | 排队、当前 GPU 分配、本月用户与 Account 卡时 | node_exporter textfile | 2 分钟 |
| Prometheus | 控制节点 | 自身状态 | 9090 | 30 秒 |

10 秒任务使用 5 秒超时，其余抓取最多等待 10 秒。DCGM 内部采样也设为 10 秒。Grafana 和 OOD 指标留给各自的后续工作包。

### 阶段 1：删除全部旧监控安装

目的：旧监控已经失效，不迁移配置、数据或 unit。三台主机都停止并删除手工安装的 node_exporter；两个 GPU 节点还删除旧 nvitop、Slurm exporter 和 DCGM 容器配置；控制节点同时删除旧 Prometheus 数据。

三台主机都执行：

```bash
sudo systemctl disable --now node_exporter.service || true
sudo rm --force \
  /etc/systemd/system/node_exporter.service \
  /usr/local/bin/node_exporter
sudo rm --recursive --force /var/lib/node_exporter
sudo systemctl daemon-reload
```

A100 和 4070 都执行：

```bash
sudo systemctl disable --now nvitop-exporter.service || true
sudo systemctl disable --now slurm-job-exporter.service || true
sudo systemctl disable --now nvidia-dcgm-exporter.service || true
sudo docker rm --force dcgm-exporter 2>/dev/null || true

sudo rm --force \
  /etc/systemd/system/nvitop-exporter.service \
  /etc/systemd/system/slurm-job-exporter.service \
  /etc/systemd/system/.slurm-job-exporter.service.swp
sudo rm --recursive --force \
  /opt/nvitop-exporter \
  /etc/dcgm-exporter \
  /etc/systemd/system/nvidia-dcgm-exporter.service.d

sudo systemctl daemon-reload
```

控制节点额外执行：

```bash
sudo systemctl disable --now prometheus.service || true
sudo rm --force \
  /etc/systemd/system/prometheus.service \
  /usr/local/bin/prometheus \
  /usr/local/bin/promtool
sudo rm --recursive --force \
  /etc/prometheus \
  /var/lib/prometheus
sudo systemctl daemon-reload
```

预期：旧监控 unit、程序、虚拟环境和历史 Prometheus 数据均不存在；`nvidia-fabricmanager`、NVIDIA 驱动、`slurmd` 和现有作业不受影响。

### 阶段 2：在全部主机安装 node_exporter

目的：提供主机级指标。以下命令分别在控制节点、A100 和 4070 执行；服务由后续 Ansible 创建。

```bash
cd /tmp

NODE_EXPORTER_TAG=$(
  curl --fail --silent --show-error \
    https://api.github.com/repos/prometheus/node_exporter/releases/latest |
  python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])'
)
NODE_EXPORTER_VERSION="${NODE_EXPORTER_TAG#v}"

curl --fail --location --remote-name \
  "https://github.com/prometheus/node_exporter/releases/download/${NODE_EXPORTER_TAG}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"

tar --extract --gzip \
  --file="node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"

sudo install --owner=root --group=root --mode=0755 \
  "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" \
  /usr/local/bin/node_exporter

/usr/local/bin/node_exporter --version
```

预期：GitHub `releases/latest` 返回当前稳定版本，三台主机显示相同版本。此时服务尚未启动是正常的。

### 阶段 3：在控制节点安装 Prometheus

目的：安装本地时序数据库和配置检查器。

```bash
cd /tmp

PROMETHEUS_TAG=$(
  curl --fail --silent --show-error \
    https://api.github.com/repos/prometheus/prometheus/releases/latest |
  python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])'
)
PROMETHEUS_VERSION="${PROMETHEUS_TAG#v}"

curl --fail --location --remote-name \
  "https://github.com/prometheus/prometheus/releases/download/${PROMETHEUS_TAG}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz"

tar --extract --gzip \
  --file="prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz"

sudo install --owner=root --group=root --mode=0755 \
  "prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus" \
  "prometheus-${PROMETHEUS_VERSION}.linux-amd64/promtool" \
  /usr/local/bin/

/usr/local/bin/prometheus --version
/usr/local/bin/promtool --version
```

预期：两个程序显示 GitHub 当前稳定版本。Ansible 稍后创建 `/var/lib/prometheus` 并加入 `180d` 和 `100GB` 两个保留上限。

### 阶段 4：在 A100 和 4070 安装 nvitop-exporter

目的：补足 DCGM 不提供的用户与进程级 GPU 指标。独立虚拟环境不会污染系统 Python。

```bash
sudo apt-get update
sudo apt-get install --yes python3-venv

sudo python3 -m venv /opt/nvitop-exporter
sudo /opt/nvitop-exporter/bin/python -m pip install --upgrade pip
sudo /opt/nvitop-exporter/bin/python -m pip install --upgrade nvitop-exporter

sudo /opt/nvitop-exporter/bin/python -m pip show nvitop-exporter
```

预期：显示 PyPI 当前稳定版本，程序位于 `/opt/nvitop-exporter/bin/nvitop-exporter`。Ansible 让它以 root 运行在 `system.slice`，跨越登录会话的 GPU 隐藏 cgroup；该 exporter 只暴露指标，没有结束进程的接口。

### 阶段 5：在 A100 和 4070 准备 DCGM Exporter 容器

目的：使用 rootful Docker 运行 DCGM Exporter。管理员手工准备 Docker、NVIDIA Container Toolkit、CDI 清单和镜像；Ansible 随后接管容器的 systemd 服务与采集配置，不安装 NVIDIA 软件包。

两个 GPU 节点都启用系统 Docker，并让标准 NVIDIA runtime 使用它：

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl enable --now docker.service docker.socket
sudo systemctl restart docker.service
```

若节点使用 CDI，生成持久设备清单。A100 的登录会话看不到 GPU，因此通过 `systemd-run` 在 `system.slice` 中执行：

```bash
sudo install --directory --mode=0755 /etc/cdi

sudo systemd-run \
  --wait \
  --pipe \
  --collect \
  /usr/bin/nvidia-ctk \
  cdi generate \
  --output=/etc/cdi/nvidia.yaml
```

4070 能访问 NVCR 时直接拉取当前镜像：

```bash
sudo docker pull nvcr.io/nvidia/k8s/dcgm-exporter:latest
```

A100 无法访问 NVCR 时，从已经拥有镜像的 4070 导出并传入，再由 rootful Docker 加载：

```bash
# RTX 4070
sudo docker save nvcr.io/nvidia/k8s/dcgm-exporter:latest |
gzip -1 > /tmp/dcgm-exporter.tar.gz

# Copy the archive to the A100 through the controller, then run on the A100.
gzip --decompress --stdout /tmp/dcgm-exporter.tar.gz |
sudo docker load
```

预期：两个节点的 rootful Docker 中都已有 `nvcr.io/nvidia/k8s/dcgm-exporter:latest`。不需要手工长期运行容器；Ansible 创建 `nvidia-dcgm-exporter.service`，以 `--gpus all`、`SYS_ADMIN` 和本地配置挂载启动它。

### 阶段 6：启用 Slurm 内置指标

Ansible 在 `slurm.conf` 加入：

```ini
MetricsType=metrics/openmetrics
```

```bash
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible

ansible-playbook playbooks/slurm.yml --check --diff
ansible-playbook playbooks/slurm.yml

curl --fail http://127.0.0.1:6817/metrics/jobs
curl --fail http://127.0.0.1:6817/metrics/nodes
curl --fail http://127.0.0.1:6817/metrics/partitions
curl --fail http://127.0.0.1:6817/metrics/scheduler
```

预期：四个端点均返回 OpenMetrics 文本。Prometheus 不采集 `/metrics/jobs-users-accts`，个人历史继续由 SlurmDBD 报表承担。

### 阶段 7：用 Ansible 配置并启动监控栈

目的：统一创建服务账号、标准目录、systemd units、容器化 DCGM 配置和基于 inventory 主机名的 Prometheus targets。控制节点还会安装一个轻量采集器，每两分钟各执行一次 `scontrol show jobs`、`scontrol show nodes` 和 `sacct`，将结果原子写入 node_exporter textfile 目录。

这个采集器只记录有界的聚合标签：Slurm Account、用户名、分区、状态和排队原因，不把 JobID、PID 或命令写入时序标签。它提供以下部署所需指标：

| 指标 | 含义 |
|---|---|
| `epic_slurm_jobs` | 按用户、Account、分区和状态统计当前作业数 |
| `epic_slurm_pending_jobs` | 按用户、Account、分区和原因统计排队作业数 |
| `epic_slurm_pending_oldest_age_seconds` | 每组排队作业中最长的等待时间 |
| `epic_slurm_gpus_allocated` | Slurm 当前分配给用户、Account 和分区的 GPU 数 |
| `epic_slurm_gpus_requested_pending` | 排队作业请求但尚未获得的 GPU 数 |
| `epic_slurm_node_gpus_configured` | 每个节点在 Slurm 中配置的 GPU 数 |
| `epic_slurm_node_gpus_allocated` | 每个节点当前由 Slurm 分配的 GPU 数 |
| `epic_slurm_node_gpus_available` | 每个节点当前未被 Slurm 分配的 GPU 数 |
| `epic_slurm_gpu_allocated_seconds` | 本自然月按用户、Account 和分区累计的 GPU 分配秒数 |
| `epic_slurm_gpu_jobs` | 本自然月按状态统计的 GPU 作业数 |
| `epic_slurm_usage_collector_last_success_unixtime` | 最近一次完整采集成功的时间 |

其中“使用量”指 Slurm 分配时长，而不是 GPU 核心实际忙碌时长。它适合统计卡时、组占比和排队需求；DCGM 与 nvitop 则用于判断拿到 GPU 后是否真正计算。采集失败时旧文件保留，避免把短暂的 SlurmDBD 故障表现为全部指标突然归零。

```bash
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible

# Preview the configuration managed by work package 6.
ansible-playbook playbooks/monitoring.yml --check --diff

# Configure node exporters, then GPU exporters, then Prometheus.
ansible-playbook playbooks/monitoring.yml
```

预期 recap：所有主机均无 `failed` 和 `unreachable`。Prometheus 启动前通过 `promtool check config`，最后等待全部 targets 变为 `UP`。

### 阶段 8：验收与幂等性

各主机：

```bash
curl --fail http://127.0.0.1:9100/metrics |
grep node_exporter_build_info
```

A100 与 4070：

```bash
curl --fail http://127.0.0.1:9400/metrics |
grep --max-count=3 '^DCGM_'

curl --fail http://127.0.0.1:5050/metrics |
grep --max-count=3 '^# HELP'

systemctl show nvitop-exporter.service \
  --property=User,Slice,ExecStart
```

控制节点：

```bash
curl --fail http://127.0.0.1:9090/-/ready

curl --fail --get \
  --data-urlencode 'query=up' \
  http://127.0.0.1:9090/api/v1/query |
python3 -m json.tool

systemctl show prometheus.service --property=User,ExecStart
systemctl status epic-slurm-usage-collector.timer --no-pager
sudo systemctl start epic-slurm-usage-collector.service
grep '^epic_slurm_' /var/lib/node_exporter/textfile_collector/slurm_usage.prom
sudo du --summarize --human-readable /var/lib/prometheus
```

工作包 6 完成时，`up` 查询应有 12 个当前 targets：Prometheus 1、node 3、DCGM 2、nvitop 2、Slurm 4，值均为 `1`。工作包 7 加入 Grafana 自身采集后增加为 13 个。Prometheus 的启动参数应包含 `180d`、`100GB` 和 `/var/lib/prometheus`。

以下 PromQL 可直接回答资源管理中的常见问题：

```promql
# 集群当前由 Slurm 分配了多少张 GPU。
sum(epic_slurm_gpus_allocated)

# 每个 Account 当前占用多少张 GPU。
sum by (account) (epic_slurm_gpus_allocated)

# 每个用户在各主机分区当前占用多少张 GPU。
sum by (user, partition) (epic_slurm_gpus_allocated)

# 每个 Account 本月累计 GPU 卡时。
sum by (account) (epic_slurm_gpu_allocated_seconds) / 3600

# 每个用户在各主机分区的本月累计 GPU 卡时。
sum by (user, partition) (epic_slurm_gpu_allocated_seconds) / 3600

# 各分区因不同原因排队的作业数与 GPU 需求。
sum by (partition, reason) (epic_slurm_pending_jobs)
sum by (partition, reason) (epic_slurm_gpus_requested_pending)

# 采集器距离上次成功已经过去多少秒；明显超过 120 秒说明数据陈旧。
time() - epic_slurm_usage_collector_last_success_unixtime
```

再次运行：

```bash
ansible-playbook playbooks/monitoring.yml
```

预期 `changed=0`，表示安装完成后的配置已被 Ansible 稳定接管。

### 停止条件

- APT 准备安装、升级或移除 NVIDIA 驱动、内核或 Fabric Manager；
- DCGM Exporter 启动影响驱动、Fabric Manager 或现有 GPU 作业；
- A100 exporter 看不到 8 张 GPU，或 4070 exporter 看不到 1 张 GPU；
- Prometheus 请求导致 slurmctld 调度周期明显变长；
- 监控任务修改 GPU 可见性或 Slurm 作业约束；
- Prometheus target 使用临时 IP，而不是 inventory 主机名；
- `/var/lib/prometheus` 位于 NFS，或缺少 180 天/100GB 上限；
- 任一监控服务故障导致 Slurm、SSH、Fabric Manager 或已有作业停止。

## 12. 工作包 7：部署 Grafana 与基础仪表盘

### 目的

在控制节点部署 Grafana OSS，并提供面向实际使用场景的集群报表。Grafana 只展示信息，不提供作业取消、节点状态修改、告警或其他控制操作。管理员仍通过 Slurm 命令行处理具体事务。

Grafana 软件由管理员手工安装当前稳定版本。Ansible 只负责：

- Grafana 基础配置和服务状态；
- Prometheus 数据源；
- 仪表盘文件夹和 provisioning；
- 仓库中的三个 EPIC 正式仪表盘；
- 上游仪表盘和少量社区参考仪表盘；
- Prometheus 的 180 天保留期、Grafana 自身采集和低频 Slurm 记账报表。

Grafana 不直接查询 MariaDB 的 Slurm 内部表。低频采集器每 10 分钟通过 `sacct` 和 `sshare` 生成聚合指标，Prometheus 仍是 Grafana 唯一数据源。

### 仪表盘组织

| 文件夹 | 用途 | 页面修改策略 |
|---|---|---|
| `Upstream` | nvitop 和 NVIDIA DCGM 等上游维护的原版仪表盘 | Ansible 管理，页面只读 |
| `Community References` | Slurm Native OpenMetrics、Node Exporter、Prometheus 和 Grafana 社区样例 | 独立参考，不被正式仪表盘引用 |
| `EPIC Operations` | EPIC 自己维护的三个场景仪表盘 | Ansible 管理，页面只读 |
| `Experiments` | 临时查询、试验面板和新仪表盘 | 可在页面中自由新建和修改 |

需要修改正式仪表盘时，先在 Grafana 中复制到 `Experiments`，完成试验后导出 Classic JSON，将 JSON 纳入仓库，再由 Ansible 发布。不要直接修改 provisioned dashboard；即使临时允许保存，下一次同步也会以仓库版本为准。

三个正式仪表盘分别回答不同问题：

- `Cluster Administration`：用户和 Account 使用量、Fair-share、排队情况、作业完成/失败/取消/超时比例、运行和等待时间等治理报表；
- `Cluster Availability`：控制器、数据库、节点、GPU、exporter、磁盘和可选 NFS 当前是否可用；资源全部被占用属于繁忙，不属于故障；
- `Cluster Overview`：把当前状态、近期趋势、调度、GPU、节点和记账摘要集中展示，实用和信息完整优先，不限制在一屏内。

默认范围分别为 30 天、24 小时和 7 天。趋势图响应页面顶部的时间选择器，可以临时查看 Prometheus 中最长 180 天的数据。仪表盘不采集 JobID、命令或工作目录。

### 操作

#### 1. 手工安装当前 Grafana OSS

在控制节点安装 Grafana 官方稳定 APT 仓库中的当前版本。以下操作只安装软件，不手工编辑 Grafana 配置；配置由下一步 Ansible 生成：

```bash
# Install the tools required by Grafana's signed APT repository.
sudo apt update
sudo apt install \
  apt-transport-https \
  software-properties-common \
  wget \
  gpg

# Install Grafana's repository signing key in the standard keyring path.
sudo mkdir -p /etc/apt/keyrings
wget -q -O - https://apt.grafana.com/gpg.key |
  gpg --dearmor |
  sudo tee /etc/apt/keyrings/grafana.gpg >/dev/null

# Add the stable Grafana OSS package repository.
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" |
  sudo tee /etc/apt/sources.list.d/grafana.list

# Preview the selected package before changing the host.
sudo apt update
apt-cache policy grafana
sudo apt-get --simulate install grafana

# Install the current stable Grafana OSS package.
sudo apt install grafana

# Record the installed version. Ansible does not pin or upgrade it.
grafana server --version 2>/dev/null || /usr/sbin/grafana-server -v
```

如果控制节点曾安装无效的旧 Grafana，应先使用 APT 删除旧包及确认不再需要的 `/etc/grafana`、`/var/lib/grafana` 内容。本工作包不为旧监控配置制作备份。

#### 2. 由 Ansible 配置 Grafana

先配置并启动 Grafana。上游和社区仪表盘的 JSON 已固定在项目仓库中，Ansible 直接复制这些文件，部署过程不访问 GitHub Raw 或 Grafana.com。来源地址、上游 commit 或 Grafana.com revision 记录在 `roles/monitoring_grafana/files/dashboards/SOURCES.yml`。只有管理员主动更新 vendored JSON 时才需要外网。

```bash
# Validate the Grafana playbook without changing the controller.
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-playbook playbooks/grafana.yml --syntax-check

# Preview the deployment. Do not add --diff here because vendored community
# dashboards are large and would flood the terminal with their complete JSON.
ansible-playbook playbooks/grafana.yml --check

# Apply the Grafana configuration and start the package-provided service.
ansible-playbook playbooks/grafana.yml
```

仓库中包含：

- nvitop exporter 上游 dashboard；
- NVIDIA DCGM exporter 上游 dashboard；
- Prometheus Stats 上游 dashboard；
- Grafana Internal Metrics 上游 dashboard；
- Slurm Native OpenMetrics `24979`；
- Node Exporter Full `1860`；
- Grafana Internal Stats `20138`。

DCGM 上游仪表盘以 Kubernetes 部署为主要场景，部分容器或 Pod 面板在当前裸机部署中没有数据是正常现象。它保持原版，仅作为 GPU 参数下钻和设计参考；EPIC 正式仪表盘只使用当前裸机实际存在的指标。

#### 3. 更新 Prometheus 和 Slurm 报表采集

Grafana 已启动后再重新运行 monitoring playbook。该步骤会把 Grafana 加入 Prometheus targets，把保留期改为 180 天，并安装 10 分钟一次的记账报表采集器：

```bash
# Preview the retention, target, and collector changes.
ansible-playbook playbooks/monitoring.yml --check --diff

# Apply the updated Prometheus configuration and report collector.
ansible-playbook playbooks/monitoring.yml
```

现有 2 分钟采集器继续负责当前作业、等待原因和 GPU 分配；新增 10 分钟采集器负责：

- 完成、失败、取消和超时作业数量；
- GPU 分配秒数；
- 作业运行时间和排队时间 histogram；
- 5 分钟以内的短作业数量；
- Account 和用户的 Fair-share、shares 与 normalized usage。

累计记账指标从 `monitoring_slurm_accounting_start_time` 开始。这个起点不得在日常运行中向后滚动，否则 Prometheus counter 会重置。Prometheus 只保留最近 180 天的采样，早于保留期的详细作业仍由 SlurmDBD 保存，并通过 `sacct`/`sreport` 查询。

#### 4. 首次登录

访问：

```text
http://epic-cluster-controller-01:3000/
```

首次初始化使用用户名 `administrator`。如果 Grafana 提示使用初始密码，则使用软件包默认初始密码登录并立即设置实验室管理密码。该密码只属于 Grafana，不是 Linux、SSH 或未来 OOD 的密码。

### 预期结果

- Grafana 服务启用并运行；
- Prometheus 数据源由文件自动创建，不需要网页中手工重复配置；
- `Upstream`、`Community References`、`EPIC Operations` 和 `Experiments` 四个文件夹存在；
- 三个 EPIC 正式仪表盘能够打开；尚未产生历史样本的面板会随采集逐步出现数据；
- `Experiments` 中由管理员创建的仪表盘不被 Ansible 覆盖；
- Prometheus 新增 Grafana target，启动参数包含 `180d` 和 `100GB`；
- 两个 Slurm 采集 timer 分别每 2 分钟和 10 分钟运行；
- OOD 的 Grafana 链接后续只需指向该固定服务地址。

### 停止条件

- Grafana playbook 尝试通过 APT 安装或升级软件；
- Grafana 直接读写 SlurmDBD 内部表；
- 监控部署改变 Slurm 调度或现有作业；
- 正式仪表盘出现告警、作业控制或节点控制功能；
- 社区参考仪表盘被正式仪表盘引用，或因为参考样例无数据而阻塞 EPIC 仪表盘部署。

## 13. 工作包 8：接入 OOD

本工作包在控制节点部署 Open OnDemand 4.2。该版本正式支持 Ubuntu 26.04。软件安装保持手工进行；Ansible 只管理门户、Slurm 适配器、IAPP、Remote Files、共享上下文、证书和服务。这样升级 OOD 不会隐式升级 Slurm 或其它节点软件。

### 13.1 最终结构

- 用户通过 `https://epic-cluster-controller-01/` 登录，使用 OOD 独立密码；客户端必须通过 DNS 或本机 hosts 将该名称解析到当前可访问的控制节点 IP；
- OOD 密码与 Linux/SSH 密码无关，在线文件为 `/etc/ood/auth/htpasswd`；
- 控制节点通过本机 Slurm 客户端提交作业，不依赖 SSH 密钥；
- IAPP 上下文统一存放在 `/srv/epic/ood/users/<用户>/ondemand/data`；
- 计算节点用 systemd automount 按需挂载 `/srv/epic/ood`，NFS 不可用只会使 OOD 会话失败，不影响 SSH、Home、本地文件和普通 Slurm 作业；
- 每台主机的 Home 仍独立。OOD 的 Remote Files 使用 rclone/SFTP 和用户现有的 `~/.ssh/epic_cluster_ed25519` 访问获权计算节点；
- JupyterLab、Code Server、ttyd、TensorBoard 和 Script 都通过 Slurm 启动，最长 32 小时；普通批处理仍允许 14 天；
- 表单只提供主机、CPU、GPU、内存、时长、工作目录和应用参数。高级 Slurm 参数由 `Additional sbatch arguments` 原样传入，最终权限仍由 Slurm Association/QoS 约束；
- Grafana 作为 OOD 导航入口；Prometheus 不直接暴露在 OOD 菜单中。
- OOD 中的 Grafana 入口固定使用 `epic-cluster-controller-01:3000`。访问 OOD 的客户端必须通过 DNS 或本机 hosts 将 `epic-cluster-controller-01` 解析到当前可访问的控制节点 IP；只修改集群节点的 `/etc/hosts` 对用户浏览器无效。

用户端没有 DNS 时，可将下面一行复制到本机 hosts 文件。当前控制节点校园网地址为 `172.16.2.182`：

```text
172.16.2.182 epic-cluster-controller-01
```

Linux/macOS 修改 `/etc/hosts`；Windows 修改
`C:\Windows\System32\drivers\etc\hosts`。控制节点 IP 变化时，只需更新这一行，OOD 和 Grafana 继续使用同一个主机名。

### 13.2 控制节点手工安装

先安装 OOD 4.2 的 Ubuntu 26.04（Resolute）软件源和运行依赖：

```bash
sudo apt install apt-transport-https ca-certificates apache2-utils nfs-kernel-server rclone jq curl wget

wget \
  -O /tmp/ondemand-release-web_4.2.0-resolute_all.deb \
  https://apt.osc.edu/ondemand/4.2/ondemand-release-web_4.2.0-resolute_all.deb

sudo apt install /tmp/ondemand-release-web_4.2.0-resolute_all.deb
sudo apt update
sudo apt install ondemand
sudo systemctl enable --now apache2 nfs-kernel-server
```

安装当前最新的 `ondemand_exporter`。这里只在安装时查询最新版本，Ansible 不固定其版本：

```bash
OOD_EXPORTER_TAG="$(curl --silent https://api.github.com/repos/OSC/ondemand_exporter/releases/latest | jq --raw-output .tag_name)"
OOD_EXPORTER_VERSION="${OOD_EXPORTER_TAG#v}"
OOD_EXPORTER_ARCHIVE="ondemand_exporter-${OOD_EXPORTER_VERSION}.linux-amd64"

wget \
  -O "/tmp/${OOD_EXPORTER_ARCHIVE}.tar.gz" \
  "https://github.com/OSC/ondemand_exporter/releases/download/${OOD_EXPORTER_TAG}/${OOD_EXPORTER_ARCHIVE}.tar.gz"

tar --extract --gzip --file="/tmp/${OOD_EXPORTER_ARCHIVE}.tar.gz" --directory=/tmp
sudo install \
  --owner=root \
  --group=root \
  --mode=0755 \
  "/tmp/${OOD_EXPORTER_ARCHIVE}/ondemand_exporter" \
  /usr/bin/ondemand_exporter
```

上面命令完成后，`/opt/ood`、`/usr/bin/ondemand_exporter`、Apache 和 NFS 服务应存在。此时不手工修改 `/etc/ood/config`，后续由 Ansible 生成。

### 13.3 计算节点手工准备

在 A100、RTX 4070 以及以后加入 OOD 的计算节点安装 NFS 客户端和 rclone：

```bash
sudo apt update
sudo apt install nfs-common rclone
```

各 IAPP 所需的应用程序按 [OOD 计算节点运行环境](ood-compute-runtime.md) 手工安装。Ansible 不负责跨 Ubuntu/驱动版本安装这些程序。

### 13.4 创建 OOD 登录密码

首次创建一个用户时使用 `-c`，之后增加或修改用户时不能再使用 `-c`，否则会覆盖整个文件：

```bash
sudo install --directory --owner=root --group=root --mode=0750 /etc/ood/auth
sudo touch /etc/ood/auth/htpasswd
sudo chown root:www-data /etc/ood/auth/htpasswd
sudo chmod 0640 /etc/ood/auth/htpasswd
sudo htpasswd /etc/ood/auth/htpasswd liuhongbo
sudo htpasswd /etc/ood/auth/htpasswd yeyuanlin
```

用户名必须与 Linux/Slurm 用户名一致。普通 Ansible 运行只会在文件不存在时创建空文件，绝不会覆盖已有密码。

密码文件备份是显式的管理员操作。需要备份时，把当时的在线文件复制到仓库并立即加密：

```bash
cd /srv/epic/repos/EPIC-Slurm-Cluster

sudo install \
  --owner="$(id --user)" \
  --group="$(id --group)" \
  --mode=0600 \
  /etc/ood/auth/htpasswd \
  ansible/vars/ood_htpasswd.vault

ansible-vault encrypt ansible/vars/ood_htpasswd.vault
```

修改 OOD 密码不要求提交代码，也不要求运行 role。只有管理员希望更新仓库备份时才重新执行上述备份操作。恢复同样是一次显式复制，正常部署流程不自动恢复密码。

### 13.5 检查清单并应用配置

确认 `ansible/inventory/group_vars/all/ood.yml` 中的 `ood_server_address` 是约定的控制节点主机名，并确认访问 OOD 的客户端能够解析该名称；确认每个计算节点 host vars 有易读的 `ood_display_name`。主机菜单与权限从 `slurm_partitions.yml`、`users.yml` 和 host vars 自动生成，不再维护第二份列表。

```bash
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible

ansible-playbook playbooks/ood.yml --check --diff
ansible-playbook playbooks/ood.yml
ansible-playbook playbooks/monitoring.yml
```

该流程会完成以下工作：

1. 生成包含控制节点 DNS 名称的自签名证书和 Basic Auth 门户；
2. 生成本地 Slurm 适配器及 OOD 页面配置；
3. 建立 `/srv/epic/ood` 用户上下文并导出给计算节点；
4. 在计算节点启用按需 NFS 挂载；
5. 发布五个 IAPP、Grafana 链接和三个 Job Composer 模板；
6. 按 `ssh_access` 为每个用户生成对应 rclone/SFTP Remote Files；
7. 启用 Job Composer 使用的控制节点 Shell，并为 Node 22 Passenger 进程禁用 V8 JIT；
8. 启动 `ondemand_exporter`，并让 Prometheus 每 2 分钟采集一次。

浏览器首次访问自签名证书时会显示警告；在校园网内确认地址正确后接受即可。

### 13.6 最小验收

```bash
systemctl is-active apache2 nfs-kernel-server ondemand_exporter
curl --silent http://127.0.0.1:9301/metrics | head
```

然后通过浏览器确认：

- OOD 独立密码能够登录；
- IAPP 的 Target host 只显示该用户有 Association 的主机；
- 提交一个短 ttyd 或 JupyterLab 会话后，作业出现在 `squeue`，页面能够连接；
- Remote Files 只显示该用户 `ssh_access` 中的主机；
- Job Composer 中存在 Basic、GPU 和 Array 三个模板；
- Job Composer 的 Open Terminal 能够打开控制节点 Shell；
- Prometheus 的 `open-ondemand` target 为 `UP`。

### 13.7 日常修改规则

- 改密码：只运行 `htpasswd`；
- 改控制节点 IP：保持 `ood_server_address` 不变，只更新客户端 DNS 或 hosts 中 `epic-cluster-controller-01` 的地址；
- 改用户可见主机：修改 Slurm 分区授权/Association 相关清单，然后运行 Association 与 OOD playbook；
- 改 IAPP：修改仓库中的 `apps/IAPP_*`，再运行 `ood.yml`；
- 升级 OOD、Passenger 或 Node 后：临时移除 `ood_pun_node_options` 复测 Job Composer terminal；若不再出现 V8 executable-memory 错误，可永久删除 `--jitless` 兼容配置；
- 新增计算节点：先按运行环境文档安装程序，再加入 inventory、Slurm 分区与用户 `ssh_access`，最后运行 `ood.yml`；
- NFS 故障：只处理 OOD 上下文服务，不要把用户 Home、Slurm 状态或普通作业迁入该 NFS。

### 13.8 本地磁盘配额与 OOD 提示

A100 节点的 `/home` 和 `/workspace` 是独立的本地 ext4 文件系统，配额只在该节点生效：

- `/home`：普通用户 soft 20 GiB、hard 30 GiB，宽限期 3 天；
- `/workspace`：普通用户 soft 1 TiB，不设 hard，宽限期 7 天；
- 配额只限制块空间，不限制文件数量；
- `/workspace` 是无备份 RAID0，只用于环境、缓存和可再生数据。

首次启用文件系统配额需要手工完成，Ansible 不修改 `fstab`，不执行 `quotacheck`，不自动 remount。A100 的 `/home` 和 `/workspace` 按以下流程初始化；控制节点也必须对 `/home` 完成相同的 `usrquota`、`quotacheck` 与 `quotaon` 初始化后，才能执行配额 playbook：

```bash
# 确认文件系统类型和挂载参数
findmnt -T /home -o TARGET,SOURCE,FSTYPE,OPTIONS
findmnt -T /workspace -o TARGET,SOURCE,FSTYPE,OPTIONS

# 在 /etc/fstab 的 /workspace ext4 行加入 usrquota 后重新挂载
sudo mount -o remount /workspace

# 初始化并启用 workspace user quota
sudo quotacheck -cum /workspace
sudo quotaon /workspace
sudo edquota -t -f /workspace      # Block grace period: 7days
```

确认两个文件系统都显示 `user quota ... is on` 后，运行：

```bash
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-playbook playbooks/disk_quotas.yml
```

控制节点的策略定义在 `ansible/inventory/host_vars/epic-cluster-controller-01.yml`：所有受管用户的 `/home` 软限额为 `5 GiB`、无硬限额、宽限期为 3 天。它是临时中转空间，不应用于长期保存数据。

该 role 只负责持续设置用户 soft/hard limit 和宽限期。每个启用配额管理的计算节点每 5 分钟生成一份以完整主机名命名的 JSON，例如 `epic-cluster-compute-a100-01.json`。OOD Dashboard 自动扫描目录并按“主机 · 文件系统”展示；报告超过 15 分钟未更新时标记为“数据已过期”。新增节点无需修改 OOD 主机列表。超过 soft 限额的 80% 时开始提示。检查结果：

```bash
sudo quota -s -u liuhongbo -f /home
sudo quota -s -u liuhongbo -f /workspace
systemctl status epic-disk-quota-collector.timer
ls -l /srv/epic/ood/quota
cat /srv/epic/ood/quota/epic-cluster-compute-a100-01.json
```

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
- 没有累计用量额度、QoS 资源限制、抢占或未经声明的并发限制；
- Prometheus 所有预期 targets 为 `UP`；
- Grafana 三个 EPIC 场景仪表盘能够加载当前已有指标；
- SlurmDBD、Prometheus、Grafana 任一单独停止时，不会导致本地 Home、普通 SSH 或已经运行的本地进程失效。

## 18. 参考资料

- [Slurm Accounting and Resource Limits](https://slurm.schedmd.com/accounting.html)
- [Slurm Resource Limits and Associations](https://slurm.schedmd.com/resource_limits.html)
- [Slurm Multifactor Priority](https://slurm.schedmd.com/priority_multifactor.html)
- [Slurm Fair Tree](https://slurm.schedmd.com/fair_tree.html)
- [Slurm 25.11 Metrics Guide](https://slurm.schedmd.com/metrics.html)
- [NVIDIA DCGM Exporter Installation](https://docs.nvidia.com/datacenter/dcgm/latest/installation/install-dcgm-exporter.html)
- [Grafana Installation on Debian or Ubuntu](https://grafana.com/docs/grafana/latest/setup-grafana/installation/debian/)
