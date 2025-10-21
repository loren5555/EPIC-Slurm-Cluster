# Quick Start（面向用户）

> 目标：3 分钟跑起来一个 IApp（Jupyter / Code-Server / Shell）

## 1) 登录与入口
- 打开 OOD 门户：<OOD_URL>
- “Interactive Apps” 里选择需要的应用：**Jupyter** / **Code-Server** / **Shell**

## 2) 提交作业（Slurm）
表单里按需填写：
- **Partition**：`cpu`（无 GPU）或 `gpu-4070`（含 GPU）
- **GPU**（如需）：`GRES=gpu:1`
- **CPU / Memory**：根据任务需要填写（请勿过量）
- **Working Directory**：推荐 `$HOME` 或项目数据目录（见存储规范）

提交后会出现**会话卡片**；状态变为 “Running/Connect” 后点击进入。

> ℹ️ 现阶段 CPU 不排队，GPU 需排队。内存/磁盘暂无硬限，请自觉控制资源，任务完成后及时清理。

## 3) 存储与路径建议
- `/home/<user>`：**容量吃紧**，将来会转为**缓存盘**。**不要**长存大文件/数据集。  
- `/workspace/<user>/`（RAID0，无备份）：用于大文件、缓存、模型/中间结果等。**务必自行备份重要成果**。  
  推荐组织：
    /workspace/<user>/
    ├─ data/ # 数据集（尽量只读）
    ├─ runs/ # 训练输出（checkpoints/logs/tensorboard）
    ├─ envs/ # venv/conda
    └─ projects/<课题>/<repo>/

## 4) 资源占用与排障速查
- 系统资源：`htop`、`free -h`、`df -h`
- GPU：`nvidia-smi`、`nvitop`
- 队列：`squeue -u $USER`、`sinfo -s`
- 若 IApp 无法进入：查看会话卡片日志；必要时在 Issue 中附上日志片段与复现步骤。

## 5) 行为规范
- 公共资源**先到先用、互相礼让**；任务结束请及时停止/清理。
- **禁止**自行安装/升级 NVIDIA 驱动、CUDA 等底层组件。
- 重要文件请**多地备份**；`/workspace` 任何单盘故障都可能导致数据不可恢复。

## 6) 遇到问题？
- 先查 **Issues/Discussions/本手册**  
- 仍未解决 → 提交 Issue（选择合适模板，尽量最小复现）
