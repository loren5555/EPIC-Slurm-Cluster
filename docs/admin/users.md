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

1. 在 GitHub 修改 `ansible/vars/users.yml`。
2. 为用户分配未占用的 UID/GID，并填写 `slurm_account`。
3. 在 `ssh_access` 中填写允许访问的完整计算主机名。
4. 根据组织和主机使用规则更新 `ansible/vars/slurm_partitions.yml`。
5. 提交 PR，说明用户需要使用的主机和资源类型，将变更合并至部署于控制节点的main分支。
6. 按[管理员可用命令](commands.md)中的 `user_onboarding.yml` 流程一次完成身份、SSH 和 Slurm Association 配置。

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

   # 再次运行脚本，确认配置已同步
   sudo /usr/bin/env \
   ANSIBLE_CONFIG=/srv/epic/repos/EPIC-Slurm-Cluster/ansible/ansible.cfg \
   /usr/bin/ansible-playbook \
   /srv/epic/repos/EPIC-Slurm-Cluster/ansible/playbooks/user_onboarding.yml
   # 此次运行应观察到输出中 changed=0。如果不为0，再运行一次。如果还不为0，联系我。
   ```
7. 为用户创建 OOD 密码

   ```Shell
   sudo /usr/bin/htpasswd /etc/ood/auth/htpasswd <username>
   ```

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
