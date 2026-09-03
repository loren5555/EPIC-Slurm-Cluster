---
layout: default
title: 快速开始
parent: 用户文档
nav_order: 1
---

# 快速开始

## 1. 打开 OOD

如果实验室 DNS 尚未配置，在本机 hosts 文件中加入控制节点地址和主机名。地址变化时以管理员通知为准：

```text
222.20.99.125 epic-cluster-controller-01
```

Linux/macOS 修改 `/etc/hosts`；Windows 修改 `C:\Windows\System32\drivers\etc\hosts`。然后打开 [Open OnDemand](https://epic-cluster-controller-01:8443/)，使用 OOD 独立密码登录。

## 2. 运行一个交互任务

1. 选择 Jupyter、Code Server、Shell 或 Script。
2. 选择目标主机分区，填写 CPU、GPU、内存、时长和工作目录。
3. 提交后等待状态变为 **Running**，再点击 **Connect**。

不需要 GPU 的任务不要申请 GPU。需要 GPU 时填写 `gpu:1` 或更大的数量；任务只能看到 Slurm 分配给它的 GPU。

## 3. 查看任务

- 点击顶部 "My Interactive Sessions" 中会显示任务状态和连接入口。
- 点击顶部 "Jobs" 可查看任务。右侧蓝色按钮可以切换任务筛选器。
- 任务输出和错误日志位于表单指定的工作目录或日志目录。

第一次使用建议先运行几分钟的短任务，确认环境、路径和程序都正常后，再提交长时间训练。
