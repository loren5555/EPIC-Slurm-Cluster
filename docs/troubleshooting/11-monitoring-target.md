---
layout: default
title: Prometheus target 或 exporter 下线
parent: 故障手册
nav_order: 11
---

# Prometheus target 或 exporter 下线

先在 Prometheus Targets 页面确认具体目标，再到该主机检查对应服务和最近日志：

```bash
systemctl --failed
systemctl status node_exporter nvitop-exporter nvidia-dcgm-exporter --no-pager
journalctl -u <service> --since today
```

只处理实际失败的服务。DCGM Exporter 使用管理员维护的 rootful Docker，不要将普通用户
加入 `docker` 组。短时下线应通知使用者，恢复后人工刷新页面确认。
