# A100 服务器维护说明
# <span style="color:red;font-weight:bold;">【重要·必看】A100服务器部署与维护须知</span>

> **请务必阅读本页内容，以确保系统安全与规范操作。**

## 计划下周部署任务调度系统，预期变更包括：

### 1. 用户账户

   a. 所有用户禁用系统密码登陆，一般用户统一使用OOD门户访问系统。

   b. 管理员权限收缩，root禁用远程登陆、管理员账号仅保留maintain。

   c. 一般用户可以通过复制自己在控制节点家目录下的ssh私钥 `$HOME/.ssh/id_ed25519`登陆，为方便传输文件等操作，暂时不加以限制。但是这种方式进程不受cgroup管控，重负载任务会挤掉正常排队的进程。发现通过ssh绕过调度系统的现象则关闭ssh登陆功能，需要排队才能使用通常的ssh连接。

### 2. 任务提交

   a. 统一使用 Interactive App 或 Job Composer 提交任务，暂时没有其它正常提交任务的方式。

   b. 通过使用 Interactive App 中的 Code Server、Jupyter Lab、Shell等方式对部署到计算节点的代码进行调试。主要做可行性调试，不要跑重负载任务。

   c. 提交的任务将根据CPU占用率、GPU占用率等任务属性，根据select/cons_tres(Slurm默认的优先级计算算法)进行排队。

### 3. 环境变更

   a. conda等环境统一放至指定目录

   b. apt暂时不更改，出现冲突，无法消解后会清理系统环境，转用LMod 或 AppTainer。

   c. 脚本运行路径及中间存储路径建议为 `/workspace/runs/group/user/XXX`

### 4. 存储变更

   a. /home 限制。每个用户home空间软上限为20G，硬上限为30G。当home路径占用空间超过20G达到3天，或达到30G时，将禁止提交任务并停止写入。后续会根据使用情况增减配额。

   b. 增加NAS网络存储，挂载点为 `/mnt/epic-SA5212H2-01`。速度较慢，但是有28T空间，RAID 6，适合用于存储训练好的模型、存档等内容。也可以在硬盘空间吃紧的时候起到临时存放的作用。

   c. workspace重组，各位同学需标记workspace中文件所属，并移动至特定目录按照下面目录结构整理。由于用户UID变更，游离文件将无法追溯属主变为无主文件，将视为无用文件删除。

   ```
   /workspace
   ├──envs 用于存储环境相关文件，例如conda、python venv、可执行文件等
   │    ├── group 1
   │    │     ├── user 1
   │    │     ├── user 2
   │    │     └── shared
   │    └── group 2
   │          ├── user 1
   │          ├── user 2
   │          └── shared
   │
   ├──data 用于存储数据集、经验数据等
   │    ├── group 1
   │    │     ├── user 1
   │    │     ├── user 2
   │    │     └── shared
   │    └── group 2
   │          ├── user 1
   │          ├── user 2
   │          └── shared
   ├──runs 用于存储任务中间变量
   │    ├── group 1
   │    │     ├── user 1
   │    │     ├── user 2
   │    │     └── shared
   │    └── group 2
   │          ├── user 1
   │          ├── user 2
   │          └── shared
   ├──temp 用于作为大空间占用软件缓存
   │    ├── group 1
   │    │     ├── user 1
   │    │     ├── user 2
   │    │     └── shared
   │    └── group 2
   │          ├── user 1
   │          ├── user 2
   │          └── shared
   ├──containers 用于后续存储容器相关内容，暂不开放。
   │    ├── group 1
   │    │     ├── user 1
   │    │     ├── user 2
   │    │     └── shared
   │    └── group 2
   │          ├── user 1
   │          ├── user 2
   │          └── shared
   └──others 用于存储其它内容
           ├── group 1
           │     ├── user 1
           │     ├── user 2
           │     └── shared
           └── group 2
               ├── user 1
               ├── user 2
               └── shared
   ```