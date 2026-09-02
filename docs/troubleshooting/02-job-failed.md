---
layout: default
title: 作业立即失败
parent: 故障手册
nav_order: 2
---

# 作业立即失败

依次检查：

1. `cd` 的工作目录是否存在；
2. Python 或 Conda 环境路径是否正确；
3. 输入文件是否存在且可读；
4. 作业日志的最后一条错误；
5. `sacct -j <job-id> --format=JobID,State,ExitCode` 的结果。

规划中的共享 `/data` 尚未上线；脚本依赖该路径时会失败。当前应使用目标节点的本地
`/workspace`，并另行保存重要结果的备份。
