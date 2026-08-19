# Quick Start

> 目标：3 分钟跑起来一个任务

## 1) 登录与入口
- 打开 OOD 门户：[Open Ondemand](http://222.20.76.128)
- “Interactive Apps” 里选择需要的应用：**Jupyter** / **Code-Server** / **Shell** / **Script**

## 2) 提交作业（Slurm）
表单里按需填写：
- **Partition**：`NVIDIA A100 Node`，现在还没有别的
- **GPU**：`GRES=gpu:1` 不需要GPU可以填0。不需要GPU的任务不需要排队。
- **CPU**：根据任务需要填写（请勿过量）
- **Working Directory**：登陆后的工作路径，默认`$HOME`

提交后会出现**会话卡片**；状态变为 “Running” 后点击"Connect"进入。

> ℹ️ 现阶段 CPU 不排队，GPU 需排队。内存无限制，请自觉控制资源，任务完成后及时清理。

## 3) 资源占用与排障速查
- 系统资源：`htop`、`free -h`、`df -h`
- GPU：`nvidia-smi`、`nvitop`
- 队列：`squeue -u $USER`、`sinfo -s`
- 磁盘限额：`quota -s`；OOD 首页显示 `/home` 与 `/workspace` 使用量，超过 soft 限额后进入宽限期
- 若任务卡在排队：查看 `squeue` 输出，确认资源请求是否合理
- 若 IApp 无法进入：查看会话卡片日志；必要时在 Issue 中附上日志片段与复现步骤。

## 4) 行为规范
- 公共资源**先到先用、互相礼让**；任务结束请及时停止/清理。
- **禁止**自行安装/升级 NVIDIA 驱动、CUDA 等底层组件。
- 重要文件请**多地备份**；`$HOME`、`/workspace` 任何单盘故障都可能导致数据不可恢复。

## 5) 遇到问题？
- 先查 **Issues/Discussions/本手册**  
- 仍未解决 → 提交 Issue（选择合适模板，尽量最小复现）
