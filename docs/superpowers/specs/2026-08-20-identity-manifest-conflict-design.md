# Ansible 身份清单内部冲突预检设计

日期：2026-08-20  
状态：用户已确认，待实施

## 目标

扩展现有 `ansible/filter_plugins/identity.py` 中的
`identity_conflicts()`，使身份 role 在修改任何主机前，同时发现
`users.yml` 清单内部和目标主机现有 NSS 身份中的 UID/GID 冲突。

## 设计

- 保留 `identity_conflicts()` 的接口、返回类型和调用位置，不新增 filter
  或 Ansible task。
- 为 `cluster_users` 按 UID 建立反向索引；同一 UID 对应多个不同用户名时，
  生成一条包含该 UID 和全部用户名的冲突信息。
- 将用户私有组与 `access_groups` 合并后按 GID 建立反向索引；同一 GID
  对应多个不同组名时，生成一条包含该 GID 和全部组名的冲突信息。
- 使用集合去重并排序，使同名重复条目不会产生虚假冲突，且输出顺序稳定。
- 清单内部冲突与现有的主机身份冲突共同返回，由 `preflight.yml` 中现有的
  `assert` 一次列出全部问题并终止 play；converge 阶段保持不变。

## 测试与验收

先为 `identity_conflicts()` 添加失败测试，再实施最小改动。测试覆盖：

- 两个用户使用相同 UID；
- 两个用户私有组使用相同 GID；
- 两个 access group 使用相同 GID；
- 用户私有组与 access group 使用相同 GID；
- 多项清单冲突能够一次汇总，且现有主机冲突检测不回归。

验收标准是上述冲突均在只读 preflight 阶段被完整、稳定地报告，且无冲突
清单继续得到空冲突列表。
