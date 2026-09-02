---
layout: default
title: Identity 预检报 UID/GID 冲突
parent: 故障手册
nav_order: 14
---

<a id="identity-uid-gid-conflict"></a>

# Identity 预检报 UID/GID 冲突

`users.yml` 是集群数字身份的唯一权威来源。不要修改清单去迎合新节点，而是将新节点
单向校准。`epic-cluster-compute-rtx4070-02` 曾遇到：

| 用户 | 节点原 UID:主 GID | 清单要求 UID:主 GID |
|---|---:|---:|
| `yeyuanlin` | `1002:1003` | `10006:10006` |
| `yanghao` | `1004:1004` | `10010:10010` |
| `xiangxuxin` | `1001:1001` | `10011:10011` |

确认这些用户已退出目标节点、该节点没有相关作业，并记录需要校准的实际账号。以每个
用户的清单值执行：

```bash
sudo groupmod --gid <expected-gid> <user>
sudo usermod --uid <expected-uid> --gid <expected-gid> <user>
sudo chown -R <user>:<user> /home/<user>
```

如果该用户在其他本地文件系统拥有文件，还必须先用 `findmnt` 和旧 UID/GID 清点，不能
只修改 `/home`。共享 NFS 必须保持断开，避免在远端文件系统上误改属主。

返回控制节点重新收敛：

```bash
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
node=<target-node>

ansible-playbook playbooks/users.yml --limit "$node" --check --diff
ansible-playbook playbooks/users.yml --limit "$node"
ansible-playbook playbooks/users.yml --limit "$node" --check --diff
```
