# OOD 计算节点运行环境

这份清单用于手工准备能够运行 EPIC IAPP 的计算节点。各节点 Ubuntu、GPU 驱动和已有 Python 环境不同，因此 Ansible 只检查和发布应用配置，不安装这些运行时。

## 所有计算节点

```bash
sudo apt update
sudo apt install nfs-common rclone openssl jq curl python3-venv
```

节点还必须具备正常工作的 Slurm 客户端/`slurmd`、MUNGE、用户表和 `~/.ssh/epic_cluster_ed25519`。先用普通 `srun` 验证节点，再处理 OOD。

## ttyd

安装发行版当前提供的版本：

```bash
sudo apt install ttyd
ttyd --version
```

## JupyterLab

为所有用户提供独立于系统 Python 的共享虚拟环境：

```bash
sudo python3 -m venv /opt/jupyterlab
sudo /opt/jupyterlab/bin/pip install --upgrade pip jupyterlab
/opt/jupyterlab/bin/jupyter-lab --version
```

## TensorBoard

```bash
sudo python3 -m venv /opt/tensorboard
sudo /opt/tensorboard/bin/pip install --upgrade pip tensorboard
/opt/tensorboard/bin/tensorboard --version
```

## Code Server

使用 code-server 官方脚本查询并安装当前稳定版到系统路径。先用 `--dry-run` 查看它将执行的操作，再正式安装：

```bash
curl --fail --silent --show-error --location https://code-server.dev/install.sh |
  sh -s -- --dry-run --method=standalone --prefix=/usr/local

curl --fail --silent --show-error --location https://code-server.dev/install.sh |
  sudo sh -s -- --method=standalone --prefix=/usr/local

code-server --version
```

不要把版本路径写进 IAPP。升级后只要 `code-server` 命令仍可找到，就不需要修改 OOD 配置。

## GPU 节点

OOD 不另行安装或管理 CUDA。GPU 节点必须先通过普通 Slurm 作业确认设备隔离：

```bash
srun \
  --partition=目标分区 \
  --gres=gpu:1 \
  --time=00:05:00 \
  nvidia-smi -L
```

## 新节点最低验收

```bash
command -v ttyd
command -v code-server
test -x /opt/jupyterlab/bin/jupyter-lab
test -x /opt/tensorboard/bin/tensorboard
```

某个运行时缺失时，只会影响对应 IAPP；不应阻止节点通过 SSH 或 Slurm 执行其它任务。
