# 用户管理

管理员负责维护使用者名单、访问范围和使用权限。用户的 Linux 身份、SSH 主机权限、Slurm Account、分区 Association 和 OOD 账号分别对应不同配置入口。

## 用户信息

用户身份和组织归属记录在：

```Shell
ansible/vars/users.yml
```

常用字段包括：

- `name`：Linux、Slurm 和 OOD 使用的用户名；
- `uid`、`gid`：集群主机统一的数字身份；
- `groups`：Linux access group；
- `slurm_account`：用户所属的 Slurm Account，定义在`ansible/vars/slurm_accounts.yml`中；
- `ssh_access`：用户可以 SSH 访问的计算主机，定义在`ansible/inventory/hosts.yml`中。

用户与组的 UID/GID 按组织分段，当前分段和说明见[用户与组 ID 说明](../id_table_example.md)。

Linux 私有组用于文件所有权，Slurm Account 用于调度和使用统计，两者分别维护。

## 新增用户

在 `cluster_users` 中复制下面的完整条目，并替换用户名、未占用的 UID/GID、
Account、Linux access group 和 SSH 主机：

```yaml
- name: exampleuser
  uid: 10099
  gid: 10099
  slurm_account: epic-rl
  home: /home/exampleuser
  shell: /bin/bash
  groups:
    - EPIC-RL
  ssh_access:
    - epic-cluster-compute-a100-01
```

其中 `groups` 必须引用 `users.yml` 中已有的 `access_groups`，`slurm_account`
必须引用 `slurm_accounts.yml` 中已有的 Account。新增组织时，先在这两个清单中
声明对应的 access group 和 Slurm Account。

完整流程如下：

1. 在 GitHub 修改 `ansible/vars/users.yml`，为用户分配未占用的 UID/GID，
   并填写完整用户条目。
2. 按需更新 `ansible/vars/slurm_partitions.yml`。如果用户的 Account 已在目标
   分区的 `allowed_accounts` 中，不需要修改；只有目标分区按 `allowed_users`
   单独授权，或 Account 尚未获得授权时才需要更新。
3. 提交 PR，说明用户需要使用的主机和资源类型，将变更合并至部署于控制节点的
   `main` 分支，并按[管理员可用命令](commands.md)同步控制节点仓库。

   ```bash
   sudo /usr/bin/git \
   -C /srv/epic/repos/EPIC-Slurm-Cluster \
   status

   sudo /usr/bin/git \
   -C /srv/epic/repos/EPIC-Slurm-Cluster \
   log --oneline -n 20

   sudo /usr/bin/git \
   -C /srv/epic/repos/EPIC-Slurm-Cluster \
   pull --ff-only origin main
   ```
4. 运行 `user_onboarding.yml`，一次完成身份、SSH、Slurm Association、磁盘配额
   和 OOD 配置：

   ```Shell
   # 运行检查，避免错误
   sudo /usr/bin/env \
   ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg \
   /usr/bin/ansible-playbook \
   /srv/epic/repos/EPIC-Slurm-Cluster/ansible/playbooks/user_onboarding.yml \
   --check

   # 运行脚本，同步配置
   sudo /usr/bin/env \
   ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg \
   /usr/bin/ansible-playbook \
   /srv/epic/repos/EPIC-Slurm-Cluster/ansible/playbooks/user_onboarding.yml

   # 再次运行，确认配置已同步
   sudo /usr/bin/env \
   ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg \
   /usr/bin/ansible-playbook \
   /srv/epic/repos/EPIC-Slurm-Cluster/ansible/playbooks/user_onboarding.yml
   # 此次运行应观察到 changed=0；如果连续两次仍不为 0，需检查配置是否正确。
   ```
5. 为用户创建 OOD 密码。用户名必须与Linux用户名完全一致才能正确获取访问权限：

   ```Shell
   sudo /usr/bin/htpasswd /etc/ood/auth/htpasswd <username>
   ```

`user_onboarding.yml` 的固定顺序是：

```text
users.yml → ssh_access.yml → slurm_associations.yml → disk_quotas.yml → ood.yml
```

OOD 密码是整个流程中唯一保留的交互式步骤。

## 调整访问权限

用户主机权限由 `ssh_access` 和 Slurm 分区授权共同决定：

- SSH 权限来自用户的 `ssh_access`；
- Slurm 权限来自分区的 `allowed_accounts`、`allowed_users` 和 `denied_users`；
- OOD 主机列表根据 Slurm 分区授权生成。

## 用户离开集群

用户离开时按以下顺序处理：

1. 通知开发者锁定或停用 Linux 身份；
2. 从目标分区收回 SSH 和 Slurm 权限；
3. 处理运行中和排队中的作业；
4. 保留历史 Account 和作业记录；
5. 根据数据保留政策处理用户文件。

用户主目录和实验数据的删除属于明确的生命周期操作，需要单独确认。
