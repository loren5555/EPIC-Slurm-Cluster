# EPIC 集群 Ansible 身份与 SSH 同步设计

日期：2026-08-11  
状态：用户已确认，待实施

## 1. 目标与范围

本阶段在新控制节点建立 Ansible 管理端，先将 A100 节点的现有用户、UID/GID 和项目组作为一次性迁移输入，形成 Git 仓库内的唯一权威清单。然后用同一套 playbook 校准控制节点，并将 4070 作为新增主机的验收对象。

本阶段不安装 Open OnDemand，不创建、迁移或保存 OOD 密码。OOD 使用的独立密码存储和认证方式留到 OOD 部署阶段确定。

## 2. 权威来源

- 迁移前，A100 当前的 NSS 用户与组表是迁移输入。
- 迁移后，`ansible/vars/users.yml` 是用户名、UID/GID、项目组和 SSH 访问范围的唯一机器可读权威来源。
- `docs/id_table.md` 保留为人类可读视图，不用于驱动配置。
- 所有主机创建同样的用户名和 UID/GID；“账号存在”不等于“有 SSH 访问权”。
- Ansible 遇到同名不同 UID/GID、同 UID/GID 不名的冲突时立即失败，不自动改号，不自动改变旧文件属主。
- `cluster_users` 定义所有集群用户；用户内的 `groups` 是附属 Unix 访问组列表。
- `access_groups` 只定义组名和 GID，不重复维护 `members`；成员关系从 `cluster_users[].groups` 单向推导。
- `cluster_users[].ssh_access` 只填写 inventory 中的完整计算节点主机名；所有用户的控制节点访问为全局规则，不在每个用户下重复声明。

## 3. 管理拓扑

- Ansible 只安装在 `epic-cluster-controller-01`。
- 控制节点使用 `administrator` 账号通过 SSH 管理计算节点，并使用已验证的免密码 sudo。
- 计算节点之间不需要直连；当前 A100 与 4070 之间不配置 ProxyJump。
- 节点离线时该节点报 `UNREACHABLE`，其他节点继续收敛；恢复后使用 `--limit` 补跑。

## 4. 用户与组同步

Ansible 在所有节点管理：

- 用户的用户名、UID、主 GID、主目录和 shell。
- 与用户同名的主组。
- `EPIC-RL`、`CGCL`、`MLLMs`、`3dv`和 `nue` 项目组及成员关系。
- 本地主目录的存在性和基本所有权。
- 普通用户系统密码保持锁定，不从 A100 复制 `/etc/shadow`。

删除用户时，本阶段只锁定账号并撤销受管 SSH 公钥，不自动删除主目录和用户文件。

## 5. SSH 单密钥模型

每个普通用户在控制节点拥有一套集群密钥：

```text
/home/<user>/.ssh/epic_cluster_ed25519
/home/<user>/.ssh/epic_cluster_ed25519.pub
```

规则如下：

- 密钥不存在时由 Ansible 在控制节点生成；已存在时永不覆盖。
- 私钥只保存在该用户的控制节点主目录，不进入 Git，Ansible 不将其 fetch 到管理仓库。
- 用户可自行将该私钥复制到个人设备，用于直接 SSH、VS Code、Agent 和 ProxyJump。
- 所有用户的集群公钥都安装到控制节点本人的 `authorized_keys`。
- 计算节点只安装 `ssh_access` 显式授权用户的公钥。
- A100 现有用户自主上传的公钥作为迁移数据保留，不自动复制到 4070，也不被第一次 Ansible 运行删除。

`users.yml` 中的 `ssh_access` 是受管公钥的唯一授权来源。控制节点可为所有用户登录；A100、4070 等计算节点分别授权。

## 6. Ansible 结构与运行

```text
ansible/
├── ansible.cfg
├── inventory/hosts.yml
├── vars/users.yml
├── playbooks/
│   ├── users.yml
│   ├── ssh_access.yml
│   ├── ood.yml
│   └── site.yml
└── roles/
    ├── identity/
    ├── ssh_access/
    ├── ood_controller/
    ├── ood_compute/
    └── ood_apps/
```

常规变更先运行：

```bash
ansible-playbook playbooks/users.yml --check --diff
ansible-playbook playbooks/ssh_access.yml --check --diff
```

确认后去掉 `--check --diff` 正式收敛。紧急手工修改受管文件后，必须将同样的变更补回 Git，否则下次 Ansible 执行会将其恢复为仓库状态。

OOD 后续作为同一 Ansible 项目中的独立模块加入：`ood_controller` 管理门户和 Web 服务，`ood_compute` 管理计算节点运行依赖与会话目录，`ood_apps` 发布本仓库中的 IAPP。新增 OOD 时只需增加这些 roles 并由 `site.yml` 引入，不修改已稳定的身份同步逻辑。OOD 独立密码文件不属于 `identity` 或 `ssh_access` role；其存储与更新方式在 OOD 实施前单独设计。

## 7. 首次迁移顺序

1. 从 A100 导出 UID 10000–19999 的用户和 GID 10000–19999、20000–20004 的组。
2. 将导出结果生成并人工审阅为 `ansible/vars/users.yml`。
3. 先对控制节点执行冲突预检，仅在无冲突后创建缺失账号。
4. 验证控制节点用户和组与 `users.yml` 一致。
5. 将 4070 作为新增节点，先运行 `--check --diff`，再正式收敛账号和组。
6. 验证 4070 全量 UID/GID 一致，但不自动获得 A100 现有的全量 SSH 权限。
7. 身份同步稳定后，再启用集群密钥生成和按节点授权分发。

## 8. 新增节点

新节点只需手工完成最小 bootstrap：正确主机名和网络、Python、UID/GID 1000 的 `administrator`、管理 SSH 公钥和免密码 sudo。然后：

1. 将主机加入 `inventory/hosts.yml` 的正确组。
2. 使用 `ansible <host> -m ping` 验证连接。
3. 使用 `--limit <host> --check --diff` 预演。
4. 使用 `--limit <host>` 正式收敛。
5. 运行身份清单比对和 SSH 登录验收。

## 9. 验收

- 控制节点与 4070 上的受管用户、UID/GID 和项目组与 `users.yml` 一致。
- 重复执行身份 playbook 时 `changed=0`。
- 冲突预检遇到同名不同号时失败，且不部分修改账号。
- 4070 没有因用户账号全量同步而自动获得 A100 的全量 SSH 公钥。
- OOD 密码文件和 `/etc/shadow` 不在本阶段的 Ansible diff 中出现。
