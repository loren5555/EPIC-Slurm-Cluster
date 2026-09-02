---
layout: default
title: 计算节点环境安装
parent: 开发者文档
nav_order: 8
---

# 计算节点环境安装

本文档记录 `epic-cluster-compute-rtx4070-02` 在执行 Ansible 前的手工环境准备方法，并作为后续 Ubuntu 24.04（Noble）GPU 计算节点的可复用操作参考。Ansible 只管理配置和服务单元，不安装 Slurm、MUNGE、NVIDIA 驱动、Docker 或 exporter 软件。

命令中的 `VERSION_HERE` 和 `sha256:DIGEST_HERE` 必须替换为基准节点 `epic-cluster-compute-rtx4070-01` 上已验证的值。不要将凭据、MUNGE key 或其内容写入仓库。

## 1. 基础系统与网络

目标环境为 Ubuntu 24.04 Noble `amd64`。先确认系统、主机名、时间、网络和 DNS：

```bash
cat /etc/os-release
dpkg --print-architecture
hostnamectl
timedatectl
ip -4 address
ip route
resolvectl status
```

该节点的固定租约目标地址为 `192.168.77.50/24`，默认网关为
`192.168.77.251`，VLAN 统一 DNS 为 `8.8.8.8` 和 `114.114.114.114`。主机保持
DHCP 客户端配置，路由器按网卡 MAC `b4:2e:99:cc:31:22` 下发固定租约。修改租约后，
主机在更新租约或重新连接网络前继续使用动态地址池中的旧地址属于正常过渡状态。
完整约定见[网络与静态地址规划](11-network-address-plan.md)。

网络验收：

```bash
ping -c 3 192.168.77.251
ping -c 3 8.8.8.8
resolvectl query download.docker.com
resolvectl query nvcr.io
```

## 2. Slurm 25.11 和 MUNGE

Ubuntu Noble 默认源只提供 Slurm 23.11，不能用于本集群。基准节点使用 Ubuntu HPC PPA `ppa:ubuntu-hpc/slurm-wlm-25.11`，已验证的部署版本为：

```text
slurmd                         25.11.4-1ppa1
slurm-client                   25.11.4-1ppa1
slurm-wlm-basic-plugins        25.11.4-1ppa1
munge                          0.5.15-4build1
libmunge2                      0.5.15-4build1
```

添加 PPA 并检查候选版本：

```bash
sudo add-apt-repository ppa:ubuntu-hpc/slurm-wlm-25.11
sudo apt-get update
apt-cache policy slurmd slurm-client slurm-wlm-basic-plugins munge libmunge2
```

先模拟：

```bash
sudo apt-get --simulate install \
  slurmd=25.11.4-1ppa1 \
  slurm-client=25.11.4-1ppa1 \
  slurm-wlm-basic-plugins=25.11.4-1ppa1 \
  munge=0.5.15-4build1 \
  libmunge2=0.5.15-4build1
```

确认不安装 `slurmctld`、`slurmdbd` 且不删除无关软件后，再正式安装：

```bash
sudo apt-get install \
  slurmd=25.11.4-1ppa1 \
  slurm-client=25.11.4-1ppa1 \
  slurm-wlm-basic-plugins=25.11.4-1ppa1 \
  munge=0.5.15-4build1 \
  libmunge2=0.5.15-4build1
```

不要安装 `slurm-wlm` 元包，它可能向计算节点引入控制或数据库组件。安装后不要手工启动 `slurmd`；等 Ansible 写入集群配置后由 role 启动。

```bash
slurmd -V
munge --version
sudo systemctl enable slurmd
```

MUNGE 必须使用控制节点现有的 `/etc/munge/munge.key`。通过受保护的临时文件传输，在新节点安装为 `munge:munge 0400`，然后立即删除临时副本。最后执行：

```bash
sudo systemctl enable --now munge
munge -n | unmunge
```

## 3. Docker 软件源

Docker 源使用 `/etc/apt/keyrings/docker.asc`。密钥缺失或过期时，按官方来源重新安装：

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL \
  https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
gpg --show-keys --with-fingerprint /etc/apt/keyrings/docker.asc
```

`/etc/apt/sources.list.d/docker.list` 使用：

```text
deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable
```

验证软件源和 Docker：

```bash
sudo apt-get update
apt-cache policy docker-ce docker-ce-cli containerd.io
docker --version
sudo systemctl is-active docker
```

Docker 版本应与基准节点保持一致；选择版本后先使用 `apt-get --simulate install` 审阅交易，再安装 `docker-ce`、`docker-ce-cli`、`containerd.io`、`docker-buildx-plugin` 和 `docker-compose-plugin`。

## 4. NVIDIA Container Toolkit

首先确认主机驱动正常：

```bash
nvidia-smi
```

安装 NVIDIA 官方软件源密钥：

```bash
curl -fsSL \
  https://nvidia.github.io/libnvidia-container/gpgkey \
  -o /tmp/nvidia-container-toolkit-key.asc
gpg --show-keys --with-fingerprint /tmp/nvidia-container-toolkit-key.asc
sudo gpg --dearmor --yes \
  --output /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  /tmp/nvidia-container-toolkit-key.asc
```

`/etc/apt/sources.list.d/nvidia-container-toolkit.list` 使用：

```text
deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://nvidia.github.io/libnvidia-container/stable/deb/$(ARCH) /
```

查询基准节点的版本：

```bash
dpkg-query -W -f='${Package}=${Version}\n' \
  nvidia-container-toolkit \
  nvidia-container-toolkit-base \
  libnvidia-container-tools \
  libnvidia-container1
```

在新节点执行 `apt-get update`，然后使用相同版本的四个包进行模拟和正式安装。安装后配置 Docker runtime：

```bash
nvidia-ctk --version
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
sudo systemctl is-active docker
```

## 5. DCGM Exporter 镜像

仓库的 systemd service 使用 `nvcr.io/nvidia/k8s/dcgm-exporter:latest` 且设置 `--pull never`。因此必须先将基准节点的精确镜像 digest 加载到新节点，但不要手工留下常驻容器。

在基准节点查询：

```bash
sudo docker image inspect \
  --format='{{index .RepoDigests 0}}' \
  nvcr.io/nvidia/k8s/dcgm-exporter:latest
```

在新节点拉取并添加 role 期望的 tag：

```bash
sudo docker pull \
  nvcr.io/nvidia/k8s/dcgm-exporter@sha256:DIGEST_HERE
sudo docker tag \
  nvcr.io/nvidia/k8s/dcgm-exporter@sha256:DIGEST_HERE \
  nvcr.io/nvidia/k8s/dcgm-exporter:latest
```

使用会自动删除的临时容器验证 GPU runtime：

```bash
sudo docker run --rm \
  --gpus all \
  --entrypoint nvidia-smi \
  nvcr.io/nvidia/k8s/dcgm-exporter:latest \
  -L
```

## 6. Exporter 文件和运行目录

Ansible 运行前必须手工准备与基准节点相同版本的 exporter 文件：

```text
/usr/local/bin/node_exporter
/opt/nvitop-exporter/bin/nvitop-exporter
```

验证：

```bash
test -x /usr/local/bin/node_exporter
test -x /opt/nvitop-exporter/bin/nvitop-exporter
sudo docker image inspect nvcr.io/nvidia/k8s/dcgm-exporter:latest
```

Slurm 的日志和 spool 目录必须与基准节点的属主、组和权限一致：

```text
/var/log/slurm
/var/lib/slurm/slurmd
```

## 7. OOD Interactive Apps 运行时

OOD 的应用目录由 `playbooks/ood.yml` 发布到控制节点，但 JupyterLab、Code
Server、ttyd 和 TensorBoard 的进程实际由 Slurm 启动在计算节点上。因此每台会出现在
OOD 分区菜单中的计算节点，都必须先安装相同的 IAPP 运行时集合。

这里的网页 VS Code 应用使用 [code-server](https://github.com/coder/code-server)，
不是 VS Code Remote-SSH 登录后按用户下载的 Microsoft `vscode-server`。不要把用户
主目录中的 `~/.vscode-server` 当作系统 IAPP 运行时。

先从已验收的基准节点记录版本；新节点必须使用同一组值：

```bash
TTYD_VERSION="$(dpkg-query -W -f='${Version}' ttyd)"
JUPYTERLAB_VERSION="$(/opt/jupyterlab/bin/python -m pip show jupyterlab | awk '/^Version:/ {print $2}')"
TENSORBOARD_VERSION="$(/opt/tensorboard/bin/python -m pip show tensorboard | awk '/^Version:/ {print $2}')"
CODE_SERVER_VERSION="$(/usr/local/bin/code-server --version | head -n1)"
printf '%s\n' \
  "ttyd=${TTYD_VERSION}" \
  "jupyterlab=${JUPYTERLAB_VERSION}" \
  "tensorboard=${TENSORBOARD_VERSION}" \
  "code-server=${CODE_SERVER_VERSION}"
```

将输出复制到节点变更记录，再在新节点设置相同的四个变量。先安装通用依赖；与其他
系统软件相同，正式安装前先审阅 APT 模拟结果：

```bash
sudo apt-get update
sudo apt-get --simulate install \
  nfs-common openssl jq curl python3-venv "ttyd=${TTYD_VERSION}"
sudo apt-get install \
  nfs-common openssl jq curl python3-venv "ttyd=${TTYD_VERSION}"
```

### 7.1 JupyterLab 和 TensorBoard

使用独立的系统虚拟环境，避免依赖任一用户的 Conda 或 Python 环境：

```bash
sudo python3 -m venv /opt/jupyterlab
sudo /opt/jupyterlab/bin/pip install --upgrade pip \
  "jupyterlab==${JUPYTERLAB_VERSION}"

sudo python3 -m venv /opt/tensorboard
sudo /opt/tensorboard/bin/pip install --upgrade pip \
  "tensorboard==${TENSORBOARD_VERSION}"
```

升级时在基准节点验证目标版本，再将相同的版本约束应用到所有计算节点。不要直接把
某个用户环境中的 `jupyter-lab` 或 `tensorboard` 暴露给系统 IAPP。

### 7.2 Code Server

历史部署使用 code-server 官方安装脚本的 standalone 方法，并将稳定入口安装为
`/usr/local/bin/code-server`。先检查脚本计划，再正式执行：

```bash
curl --fail --silent --show-error --location https://code-server.dev/install.sh |
  sh -s -- --dry-run --method=standalone --prefix=/usr/local \
  --version "${CODE_SERVER_VERSION}"

curl --fail --silent --show-error --location https://code-server.dev/install.sh |
  sudo sh -s -- --method=standalone --prefix=/usr/local \
  --version "${CODE_SERVER_VERSION}"
```

安装脚本的输出必须进入变更记录。生产节点应使用同一已验证版本；升级时先在一个保持
`DRAIN` 的节点验证 IAPP，再推广到其他节点。IAPP 只引用稳定入口，不引用带版本号的
解压目录。

### 7.3 运行时验收与版本记录

```bash
test -x /usr/local/bin/code-server
test -x /usr/bin/ttyd
test -x /opt/jupyterlab/bin/jupyter-lab
test -x /opt/tensorboard/bin/tensorboard

/usr/local/bin/code-server --version
/usr/bin/ttyd --version
/opt/jupyterlab/bin/jupyter-lab --version
/opt/tensorboard/bin/tensorboard --version
```

将四项版本和安装来源写入节点变更记录。`ood_compute` role 会检查上述四个稳定路径；
任一路径缺失或不可执行时，`playbooks/ood.yml` 会在发布节点入口前失败。

## 8. Ansible 前验收

下列检查全部通过后，才进入[Ansible 架构](02-ansible.md)和[新增节点 Checklist](07-add-node-checklist.md)中的分阶段收敛：

```bash
hostnamectl
timedatectl
getent hosts epic-cluster-controller-01
ping -c 3 192.168.77.251
slurmd -V
munge --version
munge -n | unmunge
nvidia-smi
docker --version
nvidia-ctk --version
sudo docker run --rm \
  --gpus all \
  --entrypoint nvidia-smi \
  nvcr.io/nvidia/k8s/dcgm-exporter:latest \
  -L
test -x /usr/local/bin/node_exporter
test -x /opt/nvitop-exporter/bin/nvitop-exporter
test -x /usr/local/bin/code-server
test -x /usr/bin/ttyd
test -x /opt/jupyterlab/bin/jupyter-lab
test -x /opt/tensorboard/bin/tensorboard
```

此时 `munge` 应已启动，Docker 应可用，`slurmd`、node exporter、nvitop exporter 和 DCGM exporter 的最终配置与常驻服务仍由 Ansible 管理。
