# 重要·必看 A100服务器使用须知

> **请务必阅读本页内容，以确保系统安全与规范操作。**

## 1. 使用方法
见[Quick Start](./quick_start.md)文档。

## 2. 用户账户

   - 所有用户禁用系统密码登陆，一般用户统一使用OOD门户访问系统。

   - 一般用户可以通过上传自己的公钥至计算节点家目录下的 `$HOME/.ssh/authorized_keys`登陆。通过ssh连接的终端会话无法使用GPU资源，进能够使用CPU资源。需要使用GPU资源请通过OOD门户提交任务。

## 3. 任务提交

   - 统一使用 Interactive App 或 Job Composer 提交任务，暂时没有其它正常提交GPU任务的方式。

   - 通过使用 Interactive App 中的 Code Server、Jupyter Lab、Shell等方式对部署到计算节点的代码进行调试。主要做可行性调试，最好不要跑重负载任务。

   - <span style="color:red;font-weight:bold;"> 通过使用 Job Composer、Script等方式进行训练等长时任务，详细说明见：[Job Doc](./sbatch.md)。 </span>

   - 提交的任务将根据CPU占用率、GPU占用率等任务属性，根据select/cons_tres(Slurm默认的优先级计算算法)进行排队。

## 4. 环境管理

   - pip、conda等环境统一放至指定目录
        ```bash
        # 重定向pip缓存方法
        export PIP_CACHE_DIR=/workspace/.pip-cache/$USER
        ```
        ```bash
        # 配置conda环境方法
        # 修改~/.condarc
        envs_dirs:
            - /workspace/envs/groupname/username/conda_envs
        pkgs_dirs:
            - /workspace/.conda-cache/pkgs
        auto_activate_base: false
        auto_update_conda: false

        ```
        ```bash
        # 创建新的conda环境
        conda create -p /workspace/envs/groupname/username/envname python=3.11 ...
        ```

   - 运行路径及中间存储路径建议为 `/workspace/runs/group/user/XXX`

## 5. 存储管理

   - /home 限制。每个用户home空间软上限为20G，硬上限为30G。当home路径占用空间超过20G达到3天，或达到30G时，将禁止提交任务并停止写入。

   - 增加NAS网络存储，挂载点为 `/data`。速度较慢，但是有28T空间，RAID 6，适合用于存储训练好的模型、存档等内容。也可以在硬盘空间吃紧的时候起到临时存放的作用。

   - workspace用于存储实验数据、中间产物等内容，按照下面目录结构整理。由于用户UID变更，游离文件将无法追溯属主变为无主文件，将视为无用文件删除。

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
            │
            ├──runs 用于存储任务中间变量
            │    ├── group 1
            │    │     ├── user 1
            │    │     ├── user 2
            │    │     └── shared
            │    └── group 2
            │          ├── user 1
            │          ├── user 2
            │          └── shared
            │
            ├──temp 用于作为大空间占用软件缓存
            │    ├── group 1
            │    │     ├── user 1
            │    │     ├── user 2
            │    │     └── shared
            │    └── group 2
            │          ├── user 1
            │          ├── user 2
            │          └── shared
            │
            ├──containers 用于后续存储容器相关内容，暂不开放。
            │    ├── group 1
            │    │     ├── user 1
            │    │     ├── user 2
            │    │     └── shared
            │    └── group 2
            │          ├── user 1
            │          ├── user 2
            │          └── shared
            │
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
## 6. 建议设置

- 建议修改本机hosts(用于打开浏览器的主机)，以便稳定访问各个设备
    ```bash
    # 修改/etc/hosts（linux）， "C:\Windows\System32\drivers\etc\"文件（Windows），添加如下内容
    
    # Control Node
    222.20.76.128 epic-control-node
    
    # Compute Node
    222.20.76.74  server-a100-8g-1
    
    # NFS Server
    222.20.72.39  epic-SA5212H2-01
    ```
- 建议登陆其它账号时使用无痕模式，否则切换账号时需要清理相关cookie才能登陆其它账号。
