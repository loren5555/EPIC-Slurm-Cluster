---
layout: default
title: SlurmDBD 或 MariaDB 无法连接
parent: 故障手册
nav_order: 9
---

# SlurmDBD 或 MariaDB 无法连接

```bash
sacctmgr ping
systemctl status mariadb slurmdbd --no-pager
journalctl -u slurmdbd --since today
ss -lntp | grep -E ':(3306|6819)\b'
```

依次核对数据库服务、Vault 中的凭据、`/etc/slurm/slurmdbd.conf` 权限、MUNGE、主机时间
和 Slurm 主版本。不要通过清空数据库验证连接；修复后以 `sacctmgr ping` 和一条真实作业
的 `sacct` 记录验收。
