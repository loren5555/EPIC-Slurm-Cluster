# Admin Doc（管理员）

> 面向日常运维（轻量化）：服务启停、健康检查、日志清理、账户管理指引位。

## 1) 组件概览
- Frontend：**Open OnDemand**
- Scheduler：**Slurm**（`slurmctld`、`slurmdbd`、`slurmrestd`）
- Metrics：exporters + **Prometheus** + **Grafana**
- 其它：反代/证书、SSH/BMC

> 当前策略：**无配额**；CPU 不排队、GPU 排队；内存/磁盘无硬限（依赖自觉与监控告警）。

## 2) 常用服务与启停（示例）
> 具体服务名/路径依据你的发行版与部署而定，请按实际调整。

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

Slurm：/var/log/slurm/*.log（如 slurmctld.log、slurmdbd.log）

OOD：/var/log/ondemand-nginx/

Web：/var/log/apache2/

用户会话（Nginx per-user）：/var/log/ondemand-nginx/\<user>/*

Prometheus / Grafana：根据安装路径查看 logs/

建议：

配置 logrotate，周期性压缩归档。

监控磁盘使用（尤其 /home、/var、/workspace）。

## 4) 存储与配额现状

/home：吃紧，后续迁至统一存储（当前定位为缓存盘）。

/workspace：RAID0 无备份，只放可再生/非关键数据。

用户沟通要点：请自行异地备份；重要成果切勿只放在 /workspace。

## 5) BMC 面板访问

通过堡垒机做本地转发：
```bash
ssh -N -L 8443:192.168.100.2:443 maintain@222.20.76.74
# 浏览器打开 https://localhost:8443 登录
```
账户与密码独立管理，不纳入普通用户账户体系。

## 6) 账户管理

统一在管理端执行用户创建、组分配、SSH Key 下发等。

[《管理员新增用户说明》](https://infinity-frontier.notion.site/28c835def60d8020b05cf1c03a7aff2a)


## 7) 变更管理与公告

平台变更（停机维护/策略调整/数据迁移）提前通过群/公告发布。\
平台公告文件夹位置："/etc/ood/config/announcements.d/"其中的所有未读消息都会推送至平台主页。

文档与 Issues 同步更新关键变更点：存储调整、队列策略、IApp 行为变更等。

