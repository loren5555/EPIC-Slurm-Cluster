---
layout: default
title: 手工软件准备
parent: Other
nav_order: 2
---

# 手工软件准备

部分软件受操作系统版本、GPU 驱动或上游发行方式影响，仓库中的 Ansible 只配置和
启动它们。首次部署或新增节点时，由管理员手工安装一次，再运行对应 playbook。

## SlurmDBD 与 MariaDB

先确认控制节点的 Slurm 主版本，不要在部署记账时顺便升级整个集群。安装前可用
APT 模拟检查将发生的变化：

```bash
slurmctld -V
sudo apt-get --simulate install mariadb-server slurmdbd
sudo apt install mariadb-server slurmdbd
systemctl status mariadb slurmdbd --no-pager
ss -lntp | grep -E ':(3306|6819)\b'
```

具体数据库、Vault 与配置由 `playbooks/slurmdbd.yml` 管理。部署后以
`sacctmgr ping` 的真实连接结果验收。

## OOD 计算节点运行时

每个承载 IAPP 的计算节点都需要准备基础工具和应用可执行文件：

```bash
sudo apt update
sudo apt install nfs-common rclone openssl jq curl python3-venv ttyd

sudo python3 -m venv /opt/jupyterlab
sudo /opt/jupyterlab/bin/pip install --upgrade pip jupyterlab

sudo python3 -m venv /opt/tensorboard
sudo /opt/tensorboard/bin/pip install --upgrade pip tensorboard
```

code-server 使用 standalone 安装到稳定系统前缀。先检查脚本计划，再安装：

```bash
curl --fail --silent --show-error --location https://code-server.dev/install.sh |
  sh -s -- --dry-run --method=standalone --prefix=/usr/local

curl --fail --silent --show-error --location https://code-server.dev/install.sh |
  sudo sh -s -- --method=standalone --prefix=/usr/local
```

仓库的标准路径是：

```text
/usr/local/bin/code-server
/usr/bin/ttyd
/opt/jupyterlab/bin/jupyter-lab
/opt/tensorboard/bin/tensorboard
```

版本和节点验收细节见[计算节点环境](../developer/08-compute-node-environment.md)。最终验收
是从 OOD 实际启动所需 IAPP；某个可选运行时缺失不应阻止 SSH 或其他 Slurm 作业。

## 监控二进制

node_exporter、Prometheus、Grafana 和 GPU exporter 的安装方式应按当前节点系统与仓库
变量确定。安装后运行 `playbooks/monitoring.yml` 和 `playbooks/grafana.yml`，然后人工
打开目标页确认一次。实验室部署不要求自动重启循环、自动切换或针对每个 dashboard
标题编写测试。
