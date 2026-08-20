# OOD 首次登录必读文档公告设计

## 目标

用户首次进入 Open OnDemand 时必须先阅读用户文档入口并确认，确认后才能继续使用 OOD。已确认的用户后续登录不重复显示。

## 实现

- 使用 Open OnDemand 4.2 原生 required announcement，不增加自定义页面或 JavaScript。
- 新增独立公告模板，设置稳定的 `id`、`required: true` 和中文确认按钮。
- 公告链接指向 `https://loren5555.github.io/EPIC-Slurm-Cluster/user/`。
- 由 `ood_controller` 角色将模板安装到 `announcements.d`，并沿用 PUN 重启 handler。
- 保留现有可关闭公告和不可关闭公告，不改变已有行为。

## 用户行为

OOD 根据公告 `id` 记录每位用户的接受状态。未接受时只显示必读公告，用户点击“我已阅读，开始使用”后才能进入其他页面；接受后不再显示。将来若需所有用户重新确认，发布新的公告 `id`。

## 验证

只扩展现有 OOD 角色的最小静态测试，确认任务安装了新模板，且模板包含 `required: true`、文档链接和确认按钮；不运行完整测试套件。
