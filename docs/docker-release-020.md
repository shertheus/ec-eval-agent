# 0.2.0 Docker 交付验收

日期：2026-11-15。镜像 `brain-eval:0.2.0`，Linux amd64，默认 CPU 模式。此版本增加数据检查、跨实验对比与证据 ZIP 导出，Pi 提供 11 个领域工具。

## 交付文件

| 文件或标识 | 值 |
|---|---|
| 镜像归档 | brain-eval-image.tar.gz |
| 字节数 | 4,235,867,707 |
| 归档 SHA-256 | c87aab0fec6a5f785a5c0024f6840dcf6b6426956cae5d692a9516a21560623a |
| docker inspect 镜像 ID | sha256:a337233611504f1e7aa43a190474562f996f8e61243482637dcd42a510d2ec62 |

源码仓库提供构建脚本和配置模板。运行 `bash scripts/build-image.sh` 生成镜像归档、安装入口、校验文件与模型配置模板。镜像归档作为安装交付包保存，未提交到 Git。

## 验收结果

| 检查 | 结果 |
|---|---|
| 镜像构建与归档校验 | 通过 |
| 移除镜像标签后从归档重新导入 | 通过，镜像 ID 一致 |
| 断网容器中的后端测试 | 13/13 通过 |
| 独立目录、独立容器、host 网络安装 | 通过 |
| 容器内真实 Pi + 模型任务 | 两个 Granger 实验成功 |
| 数据质量检查 | 返回节点统计并确认校验和 |
| 跨实验对比 | 同一数据，两组 alpha 参数，成功匹配 |
| 证据 ZIP | 两份归档，每份 15 个证据文件，逐文件 SHA-256 全部匹配 |

实际模型任务使用一份 3 节点、80 样本 VAR 数据，生成器边数参数 2，数据种子 17。两个实验均使用 Granger CPU、lag=1、算法种子 1、超时 30 秒，alpha 分别为 0.05 与 0.01。

Pi 在首次组织协议时将 seed 放入方法参数。后端拒绝了两份协议；Pi 将种子移到协议层后验证通过，随即完成提交、查询、收集、比较和导出。共调用 17 次工具，其中两次协议验证返回 valid=false，未发生工具执行异常。这说明验证反馈可以在算法执行前修正模型生成的配置。

验收证据见 [结构化记录](../examples/reports/system-eval/docker-020-acceptance.json) 与 [测试日志](../examples/reports/system-eval/docker-020-tests.txt)。该容器任务单独验收新增功能；10 个任务的配对评测见 [系统评测报告](system-evaluation.md)。

## 安装演示

准备模型配置和回环代理后，在交付目录运行：

```bash
sha256sum -c brain-eval-image.tar.gz.sha256
docker load -i brain-eval-image.tar.gz
bash install-local-proxy.sh
./brain-eval doctor
./brain-eval
```

直接访问模型服务时可使用标准 `install.sh`。录制时展示一次新任务的输入、实验编号、报告和证据导出。最终安装与 OBS 录制由项目作者操作；外部使用者另按 [验证表](external-validation-template.md) 记录安装体验。GPU 容器需配置 NVIDIA Container Toolkit 后独立验收。
