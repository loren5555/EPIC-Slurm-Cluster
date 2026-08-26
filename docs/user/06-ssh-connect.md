---
layout: default
title: 其它功能
parent: 用户文档
nav_order: 6
---

# 通过SSH访问
本页说明如何通过 SSH 连接获授权的计算节点、在本地 VS Code 中打开计算节点上的目录。能够通过ssh连接的AI工具也适用本说明。

## SSH 访问计算节点

计算节点位于集群内网，校园网设备不能直接连接它们。用户设备应先连接控制节点，再由 SSH `ProxyJump` 转发到目标计算节点。

### 1. 确认 SSH 权限

SSH 权限由管理员根据 `users.yml` 中的 `ssh_access` 配置。拥有 OOD 账号不代表自动拥有每台计算主机的 SSH 权限；如果目标主机没有出现在你的授权范围内，SSH 和 Remote Files 都不会开放。具体权限查看[集群用户注册文件](https://github.com/loren5555/EPIC-Slurm-Cluster/blob/main/ansible/vars/users.yml)

Ansible会为每个用户在控制节点生成一套独立的集群密钥：

```text
~/.ssh/epic_cluster_ed25519
~/.ssh/epic_cluster_ed25519.pub
```

私钥不进入 Git，也不要发送给其他人。只把自己的私钥复制到自己的访问设备。

### 2. 把控制节点私钥复制到本地设备

首先通过OOD的Shell Access或其他方式登录控制节点，查看自己的ssh私钥文件`~/.ssh/epic_cluster_ed25519`,将其内容保存到本地主机的相同位置。

完成后，在本地确认文件只属于自己：

```bash
ssh-keygen -lf ~/.ssh/epic_cluster_ed25519
```

Windows 可使用：

```powershell
ssh-keygen -lf "$env:USERPROFILE\.ssh\epic_cluster_ed25519"
```

不要用聊天工具、邮件或公共网盘传输私钥。若私钥泄露，立即通知管理员撤销并重新生成授权密钥。

### 3. 配置本地 SSH

编辑本地 `~/.ssh/config`。Windows 的文件路径为 `%USERPROFILE%\.ssh\config`；文件不存在时可以新建。下面的配置把控制节点设为跳板，并只为示例中的两个计算节点建立别名：

```sshconfig
Host epic-controller
    HostName epic-cluster-controller-01
    User <用户名>
    IdentityFile ~/.ssh/epic_cluster_ed25519
    IdentitiesOnly yes

Host epic-cluster-compute-a100-01-<用户名>
    HostName epic-cluster-compute-a100-01
    User <用户名>
    IdentityFile ~/.ssh/epic_cluster_ed25519
    IdentitiesOnly yes
    ProxyJump epic-controller

Host epic-cluster-compute-rtx4070-01-<用户名>
    HostName epic-cluster-compute-rtx4070-01
    User <用户名>
    IdentityFile ~/.ssh/epic_cluster_ed25519
    IdentitiesOnly yes
    ProxyJump epic-controller
```

只保留你实际获授权的计算节点条目，Host为连接别名可以自定义。测试连接：

```bash
ssh epic-cluster-compute-a100-01-<用户名>
```

连接成功后，可以使用同一个别名执行文件传输：

```bash
scp ./config.yaml epic-cluster-compute-a100-01-<用户名>:/workspace/runs/<group>/<user>/
rsync -av ./project/ epic-cluster-compute-a100-01-<用户名>:/workspace/runs/<group>/<user>/project/
```

SSH 登录计算节点的终端不会自动获得 GPU。需要 GPU 时，请通过 Slurm 申请作业，并在作业内运行程序。

## 在本地 VS Code 连接计算节点

VS Code 使用 **Remote - SSH** 扩展连接。它连接的是计算节点上的开发环境，不是控制节点，也不会替代 Slurm 作业调度。

1. 在本地 VS Code 安装 Microsoft 的 **Remote - SSH** 扩展。
2. 确认上面的 SSH 配置可以在终端执行 `ssh epic-cluster-compute-a100-01-<用户名>`。
3. 按 `Ctrl+Shift+P`，选择 **Remote-SSH: Connect to Host...**。
4. 选择 `epic-cluster-compute-a100-01-<用户名>` 或其他获授权别名。
5. 连接成功后，在远程窗口中打开计算节点上的项目目录，例如 `/workspace/runs/<group>/<user>/project`。

VS Code Remote-SSH 运行的是普通 SSH 会话，不会获取GPU访问权限。不要在这个会话中直接启动长时间训练；调试 GPU 程序时，在 VS Code 终端提交一个 Slurm 作业，或从 OOD Interactive App 启动开发会话。
