# EPIC Slurm 集群重建设计

日期：2026-08-04  
状态：已确认设计，待实施计划

## 1. 目标与边界

系统服务于实验室内部，核心目标只有：

1. 统一管理各主机上的 Linux 用户、UID/GID 与 SSH 公钥。
2. 使用一个 Slurm 集群实现资源登记、任务排队与 GPU/CPU 分配。
3. 保留两种主机使用模式：受管控计算节点通过 Open OnDemand 使用；自由实验主机既可直接 SSH，也可提交 Slurm 作业。
4. 每台主机使用独立本地存储，不将用户目录或运行环境依赖于网络存储。
5. 复用现有 `EPIC-Slurm-Cluster` 仓库中的文档和 OOD IApp。

本期不建设学校统一身份、LDAP/FreeIPA、自动故障转移、复杂权限系统或企业级高可用。

## 2. 系统拓扑

```text
用户
├── OOD ──> 新主控制节点 ──> managed/free 分区
└── SSH 公钥 ─────────────> free 分区中的自由实验主机

新主控制节点
├── slurmctld
├── Open OnDemand
├── 可选 slurmdbd/数据库
├── Prometheus/Grafana
└── OOD 会话目录 NFS 导出

旧控制节点
├── Slurm/MUNGE/命令行工具
├── 同步配置和恢复备份
└── 平时不运行 OOD，也不作为自动热备

计算节点
├── managed：只通过 OOD/Slurm 使用
└── free：允许 SSH，也接受 Slurm 作业
```

所有计算节点属于同一个 Slurm 集群，通过分区区分使用模式。

## 3. Slurm 分区与运行规则

### 3.1 `managed` 分区

- 用于 A100 等受管控计算节点。
- 普通用户不直接 SSH 登录。
- OOD 是主要交互入口。
- Slurm cgroup 管控作业内的 CPU、内存和 GPU 设备。
- GPU 作业必须通过 Slurm GRES 申请。

### 3.2 `free` 分区

- 用于小型、异构、自由实验主机。
- 用户使用公钥直接 SSH。
- 同时运行 `slurmd`，可接受 Slurm 作业。
- 不设置 Account/QOS 使用量限额。
- Slurm 作业仍按申请的 CPU、内存和 GPU 运行；SSH 启动的进程不受 Slurm 管理。
- 接受 SSH 进程和 Slurm 作业竞争本机资源，这是自由主机的预期行为。

### 3.3 显式选择目标主机

所有主机存储独立，因此 Slurm 不能任意把作业放到另一台没有代码和环境的机器。

OOD 表单同时提供：

- 分区选择：`managed` 或 `free`。
- 目标主机选择：根据分区动态列出节点。
- 本地工作目录：默认 `/home/$USER`。
- CPU、内存、GPU 和运行时间。

提交参数至少包含：

```text
--partition=<partition>
--nodelist=<selected-host>
```

命令行作业同样显式选择节点：

```bash
sbatch -p free --nodelist=lab-node-01 job.sh
```

## 4. 用户模型

### 4.1 唯一来源

使用 Ansible 管理本地账户。`users.yml` 是用户名、UID、GID、附属组和 SSH 公钥的机器可读唯一来源；现有 `docs/id_table.md` 仅作为迁移输入和人类可读视图。

建议结构：

```text
ansible/
├── inventory/hosts.yml
├── group_vars/
│   ├── all.yml
│   ├── controllers.yml
│   ├── managed_compute.yml
│   └── free_compute.yml
├── vars/users.yml
└── roles/
    ├── users
    ├── munge
    ├── slurm
    ├── ood
    └── nfs_client
```

### 4.2 同步规则

- 所有控制节点和计算节点创建相同用户名与 UID/GID。
- 用户 Linux 密码锁定。
- 自由实验主机安装用户的 `authorized_keys`。
- 受管控计算节点只创建账户，不部署普通用户登录公钥。
- 新主控单独维护 OOD Basic Auth 的 `.htpasswd`。
- 新增用户或更新公钥后运行 Ansible；离线主机下次补跑。
- 删除用户时先锁定账户并移除公钥，不自动删除各主机上的本地 `/home`。

## 5. 本地与网络存储

### 5.1 标准路径

| 路径 | 语义 | 存储方式 |
|---|---|---|
| `/home/<user>` | 用户本地持久文件 | 各主机独立 |
| `/scratch/<user>` | 节点本地临时/可再生数据 | 各主机独立 |
| `/srv/epic/ood` | OOD 会话与作业上下文 | 新主控本地并通过 NFS 导出 |
| `/net/epic-data` | 可选共享数据 | 外部 NFS，autofs 按需挂载 |
| `/etc/slurm` | Slurm 配置 | Ansible 分发 |
| `/var/lib/slurm/slurmctld` | 主控持久调度状态 | 主控本地 |
| `/var/lib/slurm/slurmd` | 计算节点 daemon 状态 | 各节点独立 |
| `/var/log/slurm` | Slurm 日志 | 各节点独立 |
| `/run/slurm` | PID/socket 等易失状态 | 各节点独立 |
| `/opt/ood_apps/epic` | 部署后的实验室 OOD 应用 | 主控本地 |
| `/srv/epic/repos/EPIC-Slurm-Cluster` | 维护仓库 | 主控本地 |
| `/var/backups/epic` | 配置与恢复备份 | 控制节点本地 |
| `/usr/local/sbin/epic-*` | 实验室运维脚本 | Ansible 分发 |

### 5.2 OOD 会话共享

新主控将独立文件系统或逻辑卷挂载到 `/srv/epic/ood`，并只导出该目录。所有可能执行 OOD Batch Connect 作业的节点挂载到相同绝对路径。

建议的用户数据根：

```text
/srv/epic/ood/users/<user>/ondemand/data/
```

该共享只包含会话脚本、日志、`connection.yml` 和连接上下文，不用于用户代码、模型、环境或训练数据。

OOD 会话工作目录由系统放在共享 dataroot 下；用户在 IApp 表单选择的 `working_dir` 指向目标计算节点上的本地路径。Open OnDemand Batch Connect 会在工作目录中交换连接信息，因此会话目录必须在门户与执行节点共同可见：<https://osc.github.io/ood-documentation/latest/reference/files/submit-yml/basic-bc-options.html>。

### 5.3 可选共享数据 NFS

- 挂载点为 `/net/epic-data`。
- 使用 autofs 按需挂载和有限失败等待。
- 不作为系统启动、SSH、Slurm、OOD、`/home` 或软件环境的必要依赖。
- NFS 掉线时，仅访问该路径的进程受影响。
- 共享数据不应是重要数据的唯一副本。

## 6. OOD 仓库与应用部署

现有 `EPIC-Slurm-Cluster` 仓库继续承载：

- 用户、管理员和开发文档。
- Jupyter、Code Server、ttyd、Script、TensorBoard IApp。
- Grafana/Prometheus 链接应用。

生产部署建议：

```text
/srv/epic/repos/EPIC-Slurm-Cluster/apps/
        │
        └── 发布到 /opt/ood_apps/epic/
                    │
                    └── /var/www/ood/apps/sys/<app> 软链接
```

现有 IApp 已通过 `/etc/ood/config/site.d/partitions.yml` 动态读取分区，继续保留该机制并扩展以下数据：

- 展示名称。
- Slurm 分区名。
- 节点列表。
- 每节点 CPU、内存和 GPU 上限。
- 是否允许 OOD 交互作业。

需要迁移的旧假设包括：旧 IP、旧主机名、`/workspace`、`/data`、固定 A100 分区、固定邮件域以及写死的监控链接。

## 7. 控制节点恢复策略

### 7.1 不采用 NFS 热备

Slurm 自动热备要求主控和备控始终读写同一个 `StateSaveLocation`。官方文档说明：控制器无法访问状态目录时，排队和运行作业可能被取消；普通 NFS也不是推荐的控制器状态存储：

- <https://slurm.schedmd.com/slurm.conf.html>
- <https://slurm.schedmd.com/quickstart_admin.html>

实验室现有 NFS 不够可靠，因此不让它进入 Slurm 控制链路。

### 7.2 冷备方案

- 旧控制节点安装与主控相同版本的 Slurm、MUNGE 和命令行工具。
- 同步用户、UID/GID、`/etc/slurm` 和恢复所需配置。
- 平时不运行 OOD，也不作为自动接管的第二个 `SlurmctldHost`。
- 主控定期向 `/var/backups/epic` 生成配置与状态恢复备份，并复制到旧控制节点。
- 紧急切换前必须确认原主控已经停止或隔离，避免两个主控同时运行。
- 恢复最近状态后，通过 Ansible 修改控制器地址并启动旧节点 `slurmctld`。
- 接受最近队列状态可能丢失，不承诺无感切换。

slurmdbd 和监控不作为紧急命令行调度的必要依赖。

## 8. 故障边界

| 故障 | 预期影响 | 不应影响 |
|---|---|---|
| 通用 NFS 掉线 | `/net/epic-data` 暂不可用 | SSH、Slurm、本地任务、节点启动 |
| OOD 会话 NFS 掉线 | 新 OOD 交互会话失败或现有会话卡住 | 自由 SSH、已有本地任务、Slurm daemon |
| OOD/新主控故障 | 门户和新调度操作中断 | 已运行的计算进程、自由主机 SSH |
| 自由主机离线 | 该节点作业不可调度 | 其他节点和分区 |
| Ansible 同步时节点离线 | 该节点账号暂未更新 | 已同步节点；下次补跑 |
| 旧控制节点故障 | 暂时失去冷备能力 | 主控正常调度 |

## 9. 验收标准

1. 新用户执行一次配置后，在在线节点上具有一致 UID/GID。
2. 公钥可以登录自由主机，不能直接登录受管控计算节点。
3. OOD 可以选择 `managed`/`free` 分区及明确目标节点。
4. Jupyter、Code Server、ttyd 和 Script 能在目标节点启动并生成连接信息。
5. 作业使用目标节点的本地 `/home` 或 `/scratch`。
6. 自由主机的 SSH 进程与 Slurm 作业可以同时存在。
7. 通用 NFS 断开时，SSH、Slurm和本地作业继续工作。
8. OOD 会话 NFS 断开时，故障不传播到 Slurm 控制状态。
9. 现有仓库文档不再出现失效 IP、旧节点名和旧存储路径。
10. 可以按书面流程在旧控制节点恢复命令行调度。

## 10. 实施阶段

实施计划应按以下顺序展开：

1. 清点硬件、网络、节点名和现有数据。
2. 建立 Ansible inventory 与统一用户清单。
3. 部署新主控制节点的 Slurm 基础组件。
4. 纳管受控计算节点并建立 `managed` 分区。
5. 纳管自由主机并建立 `free` 分区。
6. 建立 `/srv/epic/ood` 会话共享。
7. 迁移、修订并验证现有 IApp。
8. 配置 `/net/epic-data` 可选 NFS。
9. 建立旧控制节点冷备恢复流程。
10. 更新用户和管理员文档并完成故障验收。

