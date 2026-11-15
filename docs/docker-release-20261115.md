# Docker 交付验收：2026-11-15

镜像：brain-eval:0.1.0，Linux amd64。

- 镜像 ID：sha256:dda6966f58f8a3b70c51d138d30f1abe9d71d9df9ea0599d33929ccaf90d9ddb。
- 归档：brain-eval-image.tar.gz，4,235,862,065 字节，约 3.95 GiB。
- 归档 SHA-256：2e2a5e2b7c3f85e8f4c7f81939943a1dda48243e14b810aa3d7b0ed4c560541f。
- Python 3.11.10，PyTorch 2.7.1+cu128，CUDA 运行库 12.8，gCastle 1.0.3，Node 22.22.1，Pi 1.5.0。
- 完整 Python 包版本保存在发行目录 python-installed.txt。

## 验收证据

| 项目 | 实测结果 |
|---|---|
| 归档校验及 docker load | 通过，已有镜像缓存的同一服务器上导入用时 29.40 秒 |
| 本机代理安装入口 | 通过，使用 CPU、host 网络、独立 18766 端口和新数据目录，安装用时 2.10 秒 |
| 标准桥接安装入口 | 通过，新工作目录，初始实验列表为空 |
| 离线依赖检查 | pip check 正常，测试容器使用 --network none |
| 核心测试 | 9/9 通过 |
| 三种 gCastle 算法 | NOTEARS、GOLEM、DAG-GNN CPU，3/3 成功，exp_c88532a3afc143f0 |
| 真实模型任务 | deepseek-latest-flash，7 次工具调用全部成功，exp_f17ae4e75b6b4e33 |
| 实际算法指标 | NOTEARS CPU，2.291871 秒，F1=1、SHD=0，TP=5、FP=0、FN=0 |
| 独立结果核对 | 预测图与真值完全一致，运行 manifest 中各文件 SHA-256 匹配 |
| 环境隔离 | 应用以 1015:1015 运行，仅挂载配置、输入、结果和 Pi 状态，不挂载 Conda |
| 密钥 | 镜像环境无 API_KEY，镜像内无 /app/config/deepseek.env；配置在运行时只读挂载 |

上述算法结果只验证小规模合成数据的执行链路。算法耗时不是整个模型任务耗时；安装耗时也不包含开发者构建和依赖下载。GPU 容器未验证，默认 CPU 安装可以直接演示。

服务器证据位于项目 logs/docker-core-tests-20261115.log、logs/docker-doctor-20261115.json、logs/docker-algorithms-20261115.log、logs/docker-pi-task-20261115.jsonl 和 logs/docker-acceptance-20261115.json。

开发者验收目录为 .runtime/docker-acceptance-20261115，正式用户演示目录为 <demo-directory>。二者使用独立数据。用户的正式安装、OBS 录屏和外部使用者验证仍由用户进行。
