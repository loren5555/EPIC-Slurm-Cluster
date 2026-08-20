---
layout: default
title: 存储与运行环境
parent: 用户文档
nav_order: 4
---

# 存储与运行环境

## 存储位置


| 路径         | 用途                             | 注意事项                               |
| -------------- | ---------------------------------- | ---------------------------------------- |
| `/home`      | 代码、小型配置和少量环境文件     | 有用户配额，不适合保存大数据           |
| `/workspace` | 环境、缓存、数据集和运行结果     | 本地 RAID0，无备份，只保存可再生成内容 |
| `/data`      | 数据集、模型和需要长期保留的结果 | 网络存储，速度较慢，请保留合理目录结构 |

<span style="color:red">
`/workspace` 是RAID0阵列，为高速存储设计。磁盘吞吐大，容易损坏，5块盘的任意一块损坏会造成全体数据无法恢复。
不要在此存储重要数据，重要结果应立刻复制到独立存储进行备份。
</span>

## 推荐目录

```text
/workspace/envs/<group>/<user>/   # conda 或 venv
/workspace/data/<group>/<user>/   # 数据集和实验输入
/workspace/runs/<group>/<user>/   # 运行结果和中间文件
/workspace/temp/<group>/<user>/   # 可删除缓存
```

## 设置 pip 和 conda 缓存

pip 和 conda 默认会把下载缓存写入 `/home`。建议将缓存放到集群预留的
`/workspace/.pip-cache/` 和 `/workspace/.conda-cache/` 下，避免重复下载，也避免缓存占满 `/home`。

```bash
mkdir -p \
	"/workspace/.pip-cache/${USER}" \
	"/workspace/.conda-cache/${USER}"
```

### pip

当前 shell 立即生效：

```bash
export PIP_CACHE_DIR="/workspace/.pip-cache/${USER}"
```

如果希望以后登录自动生效，把配置写入 `~/.bashrc`：

```bash
echo 'export PIP_CACHE_DIR="/workspace/.pip-cache/${USER}"' >> ~/.bashrc
source ~/.bashrc
```

也可以使用 pip 自己的配置命令：

```bash
pip config set global.cache-dir "/workspace/.pip-cache/${USER}"
pip cache dir
```

`pip cache dir` 应显示 `/workspace/.pip-cache/<用户名>`。

### conda

将 conda 下载的包缓存（package cache）设置到用户自己的 workspace 目录：

```bash
conda config --add pkgs_dirs "/workspace/.conda-cache/${USER}"
conda config --show pkgs_dirs
```

如果还要把 conda 环境本身放到 workspace，可以另外设置环境目录：

```bash
mkdir -p "/workspace/envs/${USER}"
conda config --add envs_dirs "/workspace/envs/${USER}"
conda config --show envs_dirs
```

之后创建环境时，环境会使用 workspace 中的目录：

```bash
conda create -n my-env python=3.11
conda activate my-env
```

如果需要使用项目目录组织环境，也可以直接指定路径：

```bash
conda create --prefix "/workspace/envs/<group>/<user>/my-env" python=3.11
conda activate "/workspace/envs/<group>/<user>/my-env"
```

### 检查和清理

查看缓存位置：

```bash
echo "$PIP_CACHE_DIR"
pip cache info
conda config --show pkgs_dirs
du -sh "/workspace/.pip-cache/${USER}" "/workspace/.conda-cache/${USER}"
```

缓存可以删除，删除后只会在下次安装时重新下载：

```bash
pip cache purge
conda clean --all
```

`/workspace` 是 RAID0 且没有备份，缓存和环境都属于可再生成内容。重要代码、数据和实验结果不要只保存在缓存目录或 `/workspace` 中。
