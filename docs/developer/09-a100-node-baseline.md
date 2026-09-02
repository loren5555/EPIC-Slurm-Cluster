---
layout: default
title: A100 节点基线与资源边界
parent: 开发者文档
nav_order: 9
---

# A100 节点基线与资源边界

本文记录 `epic-cluster-compute-a100-01` 区别于普通计算节点的本机配置。Slurm、
身份、监控和 OOD 的通用配置仍以 Ansible 为准；本页只记录硬件、存储、登录会话
隔离和容器权限边界。

## 硬件与 Slurm 登记

当前仓库登记的资源为：

| 项目 | 当前值 |
|---|---:|
| CPU core | 128 |
| Slurm 可调度内存 | 1,024,000 MiB |
| GPU | 8 × NVIDIA A100 40 GB |
| 每张 GPU shard | 4 |
| CPU 超分 | 作业显式接受时，每 core 最多 4 个作业 |

机器可读值位于
`ansible/inventory/host_vars/epic-cluster-compute-a100-01.yml`。内存申请用于展示和
记账，当前不以 `ConstrainRAMSpace` 强制限制；CPU core 和 GPU 设备由 Slurm cgroup
约束。

## 本地磁盘

- 系统盘独立承载操作系统、根文件系统和 `/home`；它不是 RAID0 成员。
- 4 块数据盘组成 RAID0，并挂载为 `/workspace`。
- `/workspace` 追求容量和吞吐，不提供冗余；任意成员盘故障都可能导致整个阵列数据
  丢失。
- `/workspace` 只保存环境、缓存、数据集副本和可重建的运行结果。重要结果必须另有
  独立副本。

当前配额策略：

| 文件系统 | soft limit | hard limit | 宽限期 |
|---|---:|---:|---:|
| `/home` | 20 GiB | 30 GiB | 3 天 |
| `/workspace` | 1 TiB | 不设 hard limit | 7 天 |

文件系统必须先由超级管理员完成 `usrquota`、`quotacheck` 和 `quotaon` 初始化；Ansible
的 `disk_quota` role 负责持续设置限额，并把状态发布到 OOD 首页。当前不再使用 Slurm
Prolog 拒绝超限作业。

## SSH 登录会话与 GPU

普通 SSH、VS Code Remote 和其他登录会话位于 `user.slice`。用户可以使用 CPU、内存、
本地文件、编辑器和环境管理工具，但不能直接打开物理 GPU；GPU 计算必须进入 Slurm
作业并申请 `gpu` 或 `shard`。

节点上的本机配置文件为：

```text
/etc/systemd/system/user.slice.d/no-gpu.conf
```

其稳定策略是默认关闭设备访问，只放行 shell、PTY、随机数、FUSE 以及 NVIDIA 控制面
所需设备；不得放行 `/dev/nvidia[0-7]`、`/dev/nvidia-caps/*`、整个 `char-195:*` 或 DRM
render 节点。修改后必须在维护窗口验证三条路径：

```bash
# 普通登录会话不能计算
nvidia-smi

# Slurm 作业只能看到申请到的 GPU
srun --partition=epic-cluster-compute-a100-01 \
  --gres=gpu:1 --time=00:05:00 nvidia-smi -L

# 管理员维护入口能看到全部 GPU
sudo systemd-run --pty --slice=system.slice bash
```

完整设备清单属于主机本地安全配置。当前仓库尚未管理该 drop-in；重装或修改前应从
运行节点导出并审阅，不能根据旧笔记盲目覆盖。

## Rootful 与 rootless Docker

两种 Docker 可以共存，但用途、socket 和权限必须分开：

- rootful Docker 是系统服务。Ansible 管理的 DCGM Exporter 以 `root` 身份在
  `system.slice` 中使用它；普通用户既不属于 `docker` 组，也没有启动 rootful 容器的
  sudo 权限。
- 不得把 `/var/run/docker.sock` 改成所有用户可写，也不得仅为方便把普通用户加入
  `docker` 组；这等价于授予主机 root 能力。
- rootless Docker 使用用户自己的 daemon、socket 和数据目录，不连接 rootful socket。
  它只能在 Slurm 作业内启动，使 daemon 和容器随作业 cgroup 一起结束。
- rootless 启动脚本和 NVIDIA runtime 组合尚未由本仓库管理。发布用户命令前，必须在
  当前 Docker、NVIDIA Container Toolkit 和 cgroup 版本上重新验收；旧 Notion 命令只
  能作为历史参考。

检查权限边界：

```bash
systemctl is-active docker
getent group docker
stat -c '%A %U:%G %n' /var/run/docker.sock
systemctl status nvidia-dcgm-exporter --no-pager
```

## 不再使用的旧机制

- 不使用 Slurm Prolog 提示磁盘超限；OOD 首页已经展示配额状态。
- 不运行 `gpu_sample.sh`、`gpu_idle_detect.sh` 等 GPU 空转筛选 timer；管理员通过
  Grafana 观察异常并处理对应作业或使用者。
- 不恢复旧主机名、旧 IP、`/nas`、`/net` 或 `/nfs-drop`。

## 现场核验

涉及磁盘、设备策略或容器权限时，先读取现场再变更：

```bash
lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS
cat /proc/mdstat
findmnt /home /workspace
quotaon -p /home
quotaon -p /workspace
systemctl cat user.slice
systemctl show user.slice -p DevicePolicy -p DeviceAllow
```

节点进入 `DOWN`、`DRAIN` 或 `INVALID_REG` 时，使用
[节点状态故障](../troubleshooting/12-node-state.md)，不要顺带重建 RAID、配额或设备策略。
