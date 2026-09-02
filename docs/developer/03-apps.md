---
layout: default
title: IAPP 开发
parent: 开发者文档
nav_order: 3
---

# IAPP 开发

每个应用位于 `apps/IAPP_<name>/`，常见文件如下：

- `manifest.yml`：名称、图标和应用元数据；
- `form.yml.erb`：用户可填写的资源和应用参数；
- `submit.yml.erb`：Batch Connect 提交配置；
- `template/`：作业启动脚本；
- `view.html.erb`：连接页面和状态提示。

表单保持简短，资源字段使用统一的主机、CPU、GPU、内存、时长和工作目录。高级 Slurm 参数通过 `extra_sbatch` 保留，但不要在应用中复制权限逻辑；Association 和 QoS 由 Slurm 强制执行。

修改应用前检查：

1. 不写死旧主机名或版本路径；
2. 可执行文件通过 PATH 或稳定系统路径查找；
3. 日志和中间文件写入用户工作目录；
4. 交互任务遵守 32 小时上限；
5. 添加可复现的提交和失败验证步骤；
6. 同步更新用户文档，从 OOD 实际启动一次该 IAPP 并检查会话日志。
