---
layout: default
title: 开发记录索引
parent: Other
nav_order: 3
---

# 开发记录索引

文档重组可以移动或归纳内容，但不应删除开发过程记录。旧说明中与现状一致的操作已
并入本章和[故障手册](../troubleshooting/index.md)；过时的主机名、IP、策略和命令不直接
复制到当前操作手册，以免被误用。

## 已恢复内容的去向

| 原文件 | 当前去向 |
|---|---|
| `docs/ood-compute-runtime.md` | [手工软件准备](02-manual-software-bootstrap.md)、[计算节点环境](../developer/08-compute-node-environment.md) |
| `docs/slurm-stack-deployment-guide.md` | [实验室部署操作](01-lab-deployment.md)、[故障手册](../troubleshooting/index.md) |
| `docs/deployment.md`、`docs/quick_start.md`、`docs/sbatch.md` | 用户、管理员、开发者章节及本章 |
| `docs/admin_doc.md`、`docs/developer_doc.md`、`docs/id_table.md` | 当前管理员/开发者说明和 `ansible/vars/users.yml` |
| 2026-08-04 至 2026-08-19 被删的 9 份 plans/specs | 已按删除前原文恢复到 `docs/superpowers/`，不作为当前命令的权威来源 |

## 从 Git 查看原文

大部分旧页面在文档重组提交 `9043058` 中删除。9 份开发记录已恢复；旧入口页面已被
当前分类文档替代，不重复发布。需要核对当时现场、设计理由或未迁移细节时，仍可读取
删除前版本：

```bash
git show 9043058^:docs/ood-compute-runtime.md
git show 9043058^:docs/slurm-stack-deployment-guide.md
git show 9043058^:docs/deployment.md
git log --all --diff-filter=D --summary -- docs
```

今后清理文档时遵循两条规则：仍可执行的操作迁入 `Other`，仍可能复现的错误迁入
故障手册；纯过程记录留在 `docs/superpowers` 或新增归档索引，而不是删除。
