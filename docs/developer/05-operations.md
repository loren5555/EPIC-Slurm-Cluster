---
layout: default
title: 系统运维
parent: 开发者文档
nav_order: 5
---

# 系统运维

本页面向负责集群系统维护的开发者和超级管理员，涵盖服务、日志、节点、监控、配额和 BMC。

## 服务状态

```bash
sudo systemctl is-active apache2 nfs-kernel-server
sudo systemctl is-active slurmctld slurmdbd
sudo systemctl is-active prometheus grafana-server
```

常用日志位置：

- Slurm：`/var/log/slurm/`
- OOD 和 per-user Nginx：`/var/log/ondemand-nginx/`
- Apache：`/var/log/apache2/`
- Prometheus/Grafana：通过 systemd journal 或安装路径查看。

## Slurm 和节点

```bash
scontrol ping
sinfo -N -l
scontrol show partition
scontrol show nodes
squeue
```

节点状态、分区配置、`slurmctld`、`slurmd` 和 MUNGE 属于系统运维范围。节点进入 `DOWN`、`DRAIN` 或 `INVALID_REG` 时，先查看 Slurm 日志和节点通信状态，再决定恢复或维护。

```bash
scontrol update nodename=<node> state=drain reason="maintenance"
scontrol update nodename=<node> state=resume
```

## 配额和存储

```bash
sudo quota -s -u <user> -f /home
sudo quota -s -u <user> -f /workspace
systemctl status epic-disk-quota-collector.timer
ls -l /srv/epic/ood/quota
```

控制节点 `/home` 使用根文件系统配额；A100 的 `/home` 和 `/workspace` 是独立本地文件系统。`/workspace` 是 RAID0，只保存可再生成内容。

## BMC（现在挂了）

通过堡垒机建立本地转发：

```bash
ssh -N -L 8443:192.168.100.2:443 maintain@222.20.76.74
```

浏览器打开 `https://localhost:8443`。BMC 账户与集群用户体系分开管理，凭据不写入仓库或 Ansible 变量。

## 监控与 OOD

监控和 OOD 软件安装、服务 unit、Prometheus targets、Grafana provisioning、OOD 运行时和门户配置属于开发者维护范围。部署流程见：

- [超级管理员操作](06-superadmin.md)
- [新增节点 Checklist](07-add-node-checklist.md)
- [Ansible 架构](02-ansible.md)
- [决策记录](../superpowers/specs/)
