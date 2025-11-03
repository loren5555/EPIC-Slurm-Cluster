# Developer Doc（深度维护者 / 开发者）

> 面向后续维护者：IApp/配置开发、提交与发布、规范与最佳实践。\
> 弄不动了，自行查阅，以后再说。[Link](https://www.notion.so/infinity-frontier/A100-26d835def60d8002a8a5f4a9a657a04c?source=copy_link)

## 1) 仓库结构（建议）
    repo/
    ├─ apps/ # IApp（Batch Connect）目录
    ├─ docs/ # 本文档（GitHub Pages /docs 路线）
    ├─ .github/ISSUE_TEMPLATE/ # Issue 表单模板（已配置）
    ├─ README.md # 仓库首页
    └─ _config.yml # GitHub Pages 主题（可选）


## 2) IApp 约定与最小开发流程
- 表单尽量**少字段**、能跑就好；复杂参数暂不暴露给用户。
- 资源选择遵循平台策略（CPU 不排队、GPU 排队）；**避免过量默认值**。
- 目录/日志：优先 `$PWD` 或 `$HOME`，避免写 `/tmp` 丢失。
- 新增/修改 IApp 的 PR 应包含：
  - 可复现步骤（含分区/GPU 设置）
  - 失败路径与日志定位方式
  - 文档对应段落的最小增量更新（在 `/docs` 中）

> 如需邮件通知（作业开始/结束/失败），可在 `submit.yml.erb` 使用 Slurm 原生参数：
> ```
> script:
>   native:
>     - "--mail-type=BEGIN,END,FAIL"
>     - "--mail-user=<your@email>"
> ```


## 3) 文档维护规范（超轻量）
- 使用Markdown。
- 相同功能合并到一页，避免碎片化。
- 每次改 IApp/策略，**同步改 docs** 对应段落；PR 里一起评审。

## 4) 监控与调优（基础）
- 统计报表已上线（Prometheus/Grafana）；当前不设配额。
- 关注指标：GPU/CPU 利用、队列等待、磁盘使用热度。
- 如需自定义告警/Rule/Panel，建议以独立 PR 附上导入 JSON。

## 5) 禁止事项（再次强调）
- **严禁**更改/更新任意 NVIDIA 驱动、CUDA、Fabric Manager 等底层组件。
- 未公告前**不要**在系统级安装 Docker / runtime（后续统一上线，大概会）。

## 6) Roadmap（示例，按需维护）
- [ ] 统一存储落地与迁移指引
- [ ] 容器化运行环境（Docker/Singularity）策略
- [ ] IApp 表单精简与默认值优化
- [ ] 监控与告警规则完善
