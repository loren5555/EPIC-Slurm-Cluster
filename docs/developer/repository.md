# 仓库与变更规则

## 主要目录

```text
ansible/   身份、SSH、Slurm、监控、Grafana、OOD 和配额配置
apps/      Open OnDemand Interactive Apps 与链接应用
docs/      GitHub Pages 文档
 tests/    Python 合同测试和清单验证
```

`ansible/vars/users.yml` 是身份清单；Slurm Account 和分区授权分别由 `slurm_accounts.yml` 与 `slurm_partitions.yml` 声明；inventory/host vars 保存主机连接和硬件事实。不要从 Linux groups 或 OOD 表单反向推导 Slurm 权限。

## Pull Request

修改 IAPP、资源策略、主机权限或服务配置时，同一个 PR 更新对应文档和测试。PR 应说明：

- 改动的 source of truth；
- `--check --diff` 或本地测试结果；
- 用户侧如何验证；
- 是否影响部署顺序、权限或现有任务。

不要提交 Vault 密码、私钥、`authorized_keys` 内容或运行节点的临时状态文件。
