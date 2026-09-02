---
layout: default
title: 共享存储设计与部署
parent: 开发者文档
nav_order: 10
---

# 共享存储设计与部署

> 状态：规划中，尚未上线。当前 `/data` 不应作为作业输入、输出或唯一备份位置。

本文定义下一套共享存储的现行目标设计。旧 NFS 已失效；不恢复 `/nas`、`/net`、
`/nfs-drop` 或旧服务器名称。上线前仍需填写实际服务器、集群网段、底层文件系统、
容量、备份和维护责任人。

## 路径与职责

只保留一组稳定路径：

| 位置 | 路径 | 用途 |
|---|---|---|
| 存储服务器 | `/srv/epic/data` | 本地文件系统、配额、快照和 NFSv4 导出根 |
| 控制与计算节点 | `/data` | 用户看到的统一共享数据入口 |

`/data` 用于需要跨节点访问的数据集、模型和重要结果，不承载 `/home`、Slurm 状态、
MUNGE、OOD 会话目录、软件环境或节点启动依赖。NFS 故障只应影响主动访问 `/data` 的
进程。

## 身份与安全边界

- 所有客户端与存储服务器必须对受管用户使用一致的 UID/GID。
- 导出仅允许集群内部网段访问，保持 `root_squash`、`sync` 和
  `no_subtree_check`。
- 客户端使用 `nosuid,nodev`；共享盘不存放需要 setuid 或设备文件语义的内容。
- 初期 `sec=sys` 只允许在受控集群网络中使用。网络边界不可信时，应先设计 Kerberos
  身份和密钥生命周期，而不是开放 NFS 端口。
- 不把凭据、存储管理口令或可写的通配网段写入仓库。

## 服务端准备

上线前先确认底层文件系统、冗余、备份和容量告警。本仓库不负责创建阵列或格式化
存储设备，以免一次配置运行破坏已有数据。

服务端目标配置示意：

```text
# /etc/exports.d/epic-data.exports
/srv/epic/data <cluster-cidr>(rw,sync,sec=sys,root_squash,no_subtree_check)
```

应用前检查：

```bash
sudo exportfs -rav
sudo exportfs -v
sudo systemctl is-active nfs-server
```

## 客户端挂载

所有需要共享数据的节点使用同一个 `/etc/fstab` 记录：

```text
<storage-host>:/srv/epic/data /data nfs4 rw,hard,_netdev,nofail,nosuid,nodev,x-systemd.automount 0 0
```

这里使用 `hard`：写入中的服务器故障会等待恢复，不把超时伪装成成功。`nofail`、
`_netdev` 和 `x-systemd.automount` 让节点启动不依赖存储立即可用；它们不能保证访问
已经失联的 NFS 时永不等待。因此不要让系统服务、shell 初始化或目录遍历自动触发
`/data`。

配置和验证：

```bash
sudo install -d -m 0755 /data
sudo systemctl daemon-reload
sudo systemctl restart data.automount
systemctl status data.automount --no-pager
findmnt /data
```

不要用 `soft` 挂载保存科研数据；Linux NFS 手册明确警告它在部分情况下可能造成静默
数据损坏。

## 分阶段上线

1. 在存储服务器确认本地数据、导出范围、UID/GID、容量告警和恢复手段。
2. 先在一台非关键客户端挂载到临时路径，只验证权限、跨用户隔离和大文件读写。
3. 在一台计算节点启用 `/data`，运行短 CPU 作业和 GPU 作业验证读写。
4. 再扩展到其他计算节点，最后接入控制节点；任一步失败都停止扩展。
5. 全部验收后更新本页状态和用户文档，发布正式启用公告。

验收至少包括：

```bash
getent passwd <test-user>
findmnt -no SOURCE,FSTYPE,OPTIONS /data
sudo -u <test-user> touch /data/<test-path>/write-test
srun --partition=<partition> --time=00:05:00 test -r /data/<test-path>/write-test
```

## 故障与维护语义

- 存储离线时，禁止提交依赖 `/data` 的新作业；不重启 Slurm、SSH 或无关节点。
- `hard` 挂载上的进程可能等待服务器恢复，这是数据完整性的预期取舍。
- 维护前先公告并排查活跃 I/O；恢复后从一台客户端验证，再恢复新作业。
- 不使用旧 `/nfs-drop` 作为控制节点投递通道。节点间文件投递使用 SSH、`rsync` 或
  已有的受管 Remote Files 路径。

Linux NFS 对 `soft` 风险的说明见
[nfs(5)](https://man7.org/linux/man-pages/man5/nfs.5.html)；systemd 对
`x-systemd.automount` 与 `nofail` 的依赖语义见
[systemd.mount](https://www.freedesktop.org/software/systemd/man/latest/systemd.mount.html)。
