# EPIC Cluster — Open OnDemand Guide

> **快速链接**
> - 🧭 Quick Start（面向用户）：[quick_start](./quick_start.md)
> - 🛠 Admin Doc（管理员）：[admin_doc](./admin_doc.md)
> - 🧑‍💻 Developer Doc（开发/深度维护）：[developer_doc](./developer_doc.md)
> - ❓ 提交 Issue（问题/需求/咨询）：https://github.com/loren5555/EPIC-Slurm-Cluster/issues/new/choose

## 关于本平台
- 前端：Open OnDemand（简称 OOD）
- 调度：Slurm
- 监控：基础统计报表已上线（暂无配额/限额）
- IApp：Jupyter / Code-Server / Shell（功能简单，直接在各页标签内说明）

## 当前重要提示
> ⚠️ 请务必阅读并遵守以下约束

1. **/home 空间紧张**：后续可能切换到统一存储，当前 `/home` 未来将作为**缓存盘**使用。请将重要/大数据放入数据盘目录，做好迁移准备。
2. **禁止修改驱动/底层 NVIDIA 组件**：严禁在服务器上在线安装/更新任何 NVIDIA 相关驱动、CUDA、NVIDIA Fabric Manager 等。违者可能导致**硬件锁死**与不可恢复风险。
3. **`/workspace` 为 RAID0、无备份**：仅用于缓存/临时/可再生成数据。重要成果请自行异地/云盘备份。
4. **BMC 控制台需 SSH 转发**：  
   ```bash
   ssh -N -L 8443:192.168.100.2:443 maintain@222.20.76.74
   # 之后浏览器访问 https://localhost:8443
   # 账户与密码独立管理（向管理员索取）
5. **资源与队列策略（现阶段）**：
    CPU：不限、不排队（请自觉使用合适核数）
    GPU：排队（Slurm 队列）
    内存/磁盘：暂不设限（请谨慎申请/占用，避免影响他人）
    容器/ Docker：后续可能上线。上线前请不要私自安装相关系统级组件。
