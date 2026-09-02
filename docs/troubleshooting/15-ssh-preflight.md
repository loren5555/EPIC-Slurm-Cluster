---
layout: default
title: SSH 预检报受管用户不存在
parent: 故障手册
nav_order: 15
---

<a id="ssh-missing-managed-user"></a>

# SSH 预检报受管用户不存在

典型错误是 `SSH preflight failed for <user>`。所有集群用户必须先在每个计算节点上拥有
一致身份；`ssh_access` 只决定是否安装公钥。

```bash
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
node=<target-node>
user=<missing-user>

ansible-playbook playbooks/users.yml --limit "$node"
ansible "$node" --become -m ansible.builtin.command -a "getent passwd $user"

ansible-playbook playbooks/ssh_access.yml \
  --limit "controllers:$node" \
  --check --diff
ansible-playbook playbooks/ssh_access.yml \
  --limit "controllers:$node"
```

SSH 工作包的 limit 必须同时包含 `controllers` 和新节点，因为公钥来源在控制节点。
