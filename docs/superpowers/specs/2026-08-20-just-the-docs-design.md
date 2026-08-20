# Just the Docs 最小迁移设计

## 目标

在不增加 GitHub Actions、不迁移现有 Markdown、不引入新的构建工具的前提下，为 EPIC 文档增加清晰的左侧分层目录，并改善默认排版。

## 实现范围

- 继续使用 GitHub Pages 内置的 Jekyll 构建与现有发布来源。
- 将根目录 `_config.yml` 从 `jekyll-theme-minimal` 改为固定版本的 Just the Docs remote theme。
- 启用左侧导航、站内搜索，并在页面右上角保留 GitHub 仓库入口。
- 不增加顶部选项卡、深度定制 CSS、Gemfile 或 GitHub Actions 工作流。
- 排除 `docs/superpowers/`，避免设计记录和实施计划出现在公开站点。

## 导航结构

正式文档通过 YAML front matter 形成三组两级导航：

- 用户文档：快速开始、提交任务、排队与优先级、存储与环境、其它功能、排障。
- 管理员文档：用户管理、任务管理、管理员命令。
- 开发者文档：Ansible、应用开发、文档维护、运维、仓库结构、超级管理员操作。

根 README 继续作为站点首页；`docs/index.md` 作为文档导航页。现有正文和 Markdown 链接不改。

## 验证

- 扩展现有文档结构测试，检查 remote theme、插件、内部目录排除项以及三组父子导航元数据。
- 只运行该聚焦测试和 `git diff --check`。
- 当前环境不增加 Ruby/Jekyll 依赖，因此不做本地完整渲染；GitHub Pages 的首次构建结果作为视觉反馈来源。
