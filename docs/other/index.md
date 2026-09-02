---
layout: default
title: Other
nav_order: 7
has_children: true
---

# Other

这里保存不属于用户、管理员或开发者日常说明，但对一次部署、手工准备软件和追溯
历史决策仍有价值的操作记录。它们不应因为文档重组而被删除。

- [实验室部署操作](01-lab-deployment.md)：按依赖顺序完成一次可用部署。
- [手工软件准备](02-manual-software-bootstrap.md)：Ansible 不负责安装的软件与运行时。
- [开发记录索引](03-development-records.md)：已删除旧文档的内容去向和 Git 取回方法。

本章采用实验室标准：完成一次真实调用即可验收。服务中断先通知使用者，恢复后由
管理员人工确认；不为低频、肉眼可判断的场景增加自动恢复或重复断言。
