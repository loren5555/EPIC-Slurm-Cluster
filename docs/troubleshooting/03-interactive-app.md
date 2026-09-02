---
layout: default
title: Interactive App 无法连接
parent: 故障手册
nav_order: 3
---

# Interactive App 无法连接

确认会话卡片中的作业仍在运行，再查看会话日志。常见原因是工作目录不存在、请求超过
主机上限，或计算节点缺少应用运行时。

在对应计算节点按实际应用检查可执行文件：

```bash
test -x /usr/local/bin/code-server
test -x /usr/bin/ttyd
test -x /opt/jupyterlab/bin/jupyter-lab
test -x /opt/tensorboard/bin/tensorboard
```

缺少哪个就只补哪个，安装方法见
[Other：手工软件准备](../other/02-manual-software-bootstrap.md)。不要仅因一个 IAPP 缺失
而将整个节点或 Slurm 下线。
