# 安装与开发

面向首次使用者的完整步骤见 [README](../README.md)，离线镜像与代理配置见 [Docker 快速安装](docker-quickstart.md)。所有命令以当前仓库或交付目录为基准，不要求固定的用户名、Conda 环境名或 SSH 别名。

## 运行模式

| 模式 | 依赖 | 入口 |
|---|---|---|
| Docker CPU | Linux x86_64、Docker、用户访问权限 | bash install.sh |
| Docker 宿主机代理 | 上述环境，以及宿主机可访问的 HTTP 代理 | bash install-local-proxy.sh |
| Docker CUDA | Docker、兼容 NVIDIA 驱动与 Container Toolkit | BRAIN_EVAL_GPU=0 bash install.sh |
| 源码开发 | Python 3.11、Node >=22.19、锁定依赖 | bash scripts/dev.sh serve |

默认容器名是 brain-eval，可用 BRAIN_EVAL_CONTAINER 修改。默认桥接端口是容器内 8765，host 网络预设使用 18765。BRAIN_EVAL_PORT 可以指定未占用端口。不同实例须使用独立安装目录。

## 配置文件

从 config/deepseek.env.example 复制出 config/deepseek.env，填入密钥、Base URL 和账户允许的模型名，权限设为 600。该文件不提交到 Git。示例配置中的官方模型名不等同于任意网关模型名，出现 403 时应检查账户权限，而非反复更换密钥。

代理设置使用 HTTP_PROXY、HTTPS_PROXY 和 NO_PROXY。后端回环通信应在 NO_PROXY 中排除。容器桥接模式不能通过 127.0.0.1 访问宿主机代理，使用宿主机回环代理时选择 Linux host 网络入口。

## 复用已有开发环境

确认已有环境满足 backend/requirements.lock.txt 与 CUDA 需求后，可以使用环境变量指定 Python 和 Node，不改共享环境：

```bash
export BRAIN_EVAL_PYTHON=/absolute/path/to/existing/python
export BRAIN_EVAL_NODE=/absolute/path/to/node
bash scripts/dev.sh test
bash scripts/dev.sh serve
```

上述路径是占位符，必须替换为实际可执行文件。或者在被 Git 忽略的 .runtime/python 和 .runtime/node 建立符号链接。读取源码的后端由 dev.sh 设置 PYTHONPATH，无需依赖另一个项目的安装路径。

## 验证

```bash
bash scripts/dev.sh test
```

启动独立测试后端后，可运行：

```bash
PYTHONPATH=backend .runtime/python scripts/integration_test.py
PYTHONPATH=backend .runtime/python scripts/restart_test.py
(cd agent && ../.runtime/node test-extension.mjs)
```

这些命令要求已经建立 .runtime 运行时链接。integration_test 创建真实算法任务并注入取消和超时，不用于正式运行队列。restart_test 启动独立临时后端。Pi SDK 测试不调用模型，不能替代真实自然语言端到端任务。

## 验收范围

2026-11-15 已完成镜像构建、导出、导入、新 CPU 容器安装、9 项核心测试、算法小样例和真实模型工具链验收。GPU 容器、跨机器安装和外部使用者验证未完成，见 [发布记录](docker-release-20261115.md)。
