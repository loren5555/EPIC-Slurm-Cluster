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

## 6) 账户管理

统一在管理端执行用户创建、组分配、SSH Key 下发等。

[用户ID、组ID、统计账户表](id_table.md)

[《管理员新增用户说明》](https://infinity-frontier.notion.site/28c835def60d8020b05cf1c03a7aff2a)


## 7) 变更管理与公告

平台变更（停机维护/策略调整/数据迁移）提前通过群/公告发布。\
平台公告文件夹位置："/etc/ood/config/announcements.d/"其中的所有未读消息都会推送至平台主页。

文档与 Issues 同步更新关键变更点：存储调整、队列策略、IApp 行为变更等。

