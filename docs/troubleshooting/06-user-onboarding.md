---
layout: default
title: 用户配置工作包失败
parent: 故障手册
nav_order: 6
---

# 用户配置工作包失败

先保留失败 task 和目标主机，不要继续完整 `site.yml`。`user_onboarding.yml` 的顺序是：

```text
users.yml → ssh_access.yml → slurm_associations.yml → disk_quotas.yml → ood.yml
```

身份预检失败时使用 [UID/GID 冲突](14-identity-conflict.md)，SSH 预检失败时使用
[SSH 预检缺少用户](15-ssh-preflight.md)。修复当前阶段后从该工作包继续，不要绕过
预检或同时修改无关服务。
