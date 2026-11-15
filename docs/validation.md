# 首版验证记录

日期：2026-11-09。以下只记录实际完成的检查，不是课程正式实验结果。

## 环境

开发者验收服务器：Ubuntu 24.04.3，Linux x86_64。两张NVIDIA RTX 5090，每张约32GB，驱动580.178.04。开发复用 `开发者现有 Python 3.11 环境`，没有执行pip或conda安装/升级。Python 3.11.10、PyTorch 2.7.1+cu128、gCastle 1.0.3、NumPy 1.26.4、SciPy 1.11.4。实际GPU矩阵乘法通过。开发样例在GPU 1运行，未停止其他任务。

前端使用已有Node 22.22.1与项目本地Pi 1.5.0。服务器直连软件源超时，Node依赖在本地准备后传到项目目录；Linux Node实际加载Pi并输出版本，SDK扩展测试通过。

## 已完成

| 检查 | 结果 | 证据 |
|---|---|---|
| 9项核心测试 | 通过 | tests/test_core.py；服务器logs/unit-tests.txt |
| NOTEARS CPU、GOLEM CUDA、DAG-GNN CUDA | 3/3运行成功 | exp_3cd6da4650c04e56 |
| Granger CPU、Neural-GC cMLP CUDA | 2/2运行成功 | exp_9397dfd98ffc4097 |
| 实际子进程、多种子、报告生成 | 通过 | exp_fadcf1967cf44ae6 |
| 运行中和排队任务取消 | 通过 | exp_220662060015471f |
| 超时处理与失败披露 | 通过；该测试预期产生失败任务 | exp_36848a4a06a94c39 |
| 独立后端停止/重启 | 中断状态保留、协议保留、显式重试和取消通过 | scripts/restart_test.py |
| 真实Pi SDK加载扩展 | 8个领域工具加载，bash未激活 | agent/test-extension.mjs |
| Pi工具调用后端 | 返回5种方法能力目录 | agent/test-extension.mjs |
| 原版gCastle wheel兼容检查 | 生成数据和3种gCastle算法通过，其中GOLEM/DAG-GNN在CUDA运行 | scripts/stock_gcastle_test.py；logs/stock-gcastle.txt |
| Shell与Python语法检查 | 通过 | bash -n，compileall |
| README中文字符 | 2912，统计于本次初稿 | 不含英文、数字；可随后续编辑变化 |

实验编号对应服务器 `workspace/experiments/<编号>/`。日志和结果文件保留，可检查每个任务的配置、环境、图和指标。小样例预算很短，不能把其F1值用作方法优劣结论。

## 发现并处理的兼容问题

现有Conda环境的gCastle simulator.py已将NetworkX旧的numpy_matrix接口改为numpy_array；原版PyPI包没有这些修改。若只按包版本构建镜像，会漏掉兼容处理。

项目增加 `brain_eval/compat.py`，仅在算法或数据生成进程内提供NetworkX 3兼容别名，不修改安装目录。使用PyPI原版gCastle 1.0.3 wheel优先加载后重新运行生成器、NOTEARS、GOLEM和DAG-GNN，实际通过。三个已用算法的主类文件与原版wheel哈希一致。现有环境中的非线性NOTEARS还多一行注释，本版本没有调用该方法。

Neural-GC源码固定到commit c3263d40433aaf3acc94c27a0c1abf9b8e9fcedf，已对照该提交下载内容。相对导入修改及许可证记录在vendor目录。第三方源码不计入个人有效代码。

## 2026-11-15：真实模型端到端任务

通过本机 HTTP 代理 18083 和 SSH 回环端口转发，Pi 使用内网 LiteLLM 的 `deepseek-latest-flash` 完成自然语言任务。配置中的 `deepseek-latest` 返回模型权限错误，本次通过进程环境临时覆盖模型名，没有修改密钥文件。

任务：线性 SEM，5 节点、200 样本，生成器边数参数 4，数据种子 42；gCastle NOTEARS CPU，算法种子 42，max_iter=20、lambda1=0.1、w_threshold=0.3，超时 120 秒。

- 实验：`exp_bcaa6c7d1aa44624`，运行：`run_e645b02d77844a52`，一次成功，无重试。
- Pi 完成 7 次模型请求和 7 次成功工具调用：能力查询、环境检查、生成数据、验证协议、提交、查询状态、导出报告。
- 实际真值边数为 5。请求边数是 ER 生成器参数，不保证生成精确边数。
- F1=1.0、SHD=0、TP=5、FP=0、FN=0，运行计时 4.096682 秒。独立读取 truth.npy 和 graph.npz，确认两者去对角后的有向邻接矩阵完全一致。
- 校验了 manifest 中 5 个文件的 SHA-256，全部匹配。HTML、CSV、JSON 和 SVG 已导出。
- 本地报告副本：`validation/20261115-pi-task/reports/`；核验记录：`validation/20261115-pi-task/audit.json`。服务器完整交互日志：`logs/pi-simple-task-20261115.jsonl`。

结果解释仍需审阅：Pi 的文字回答把“200>5”视为样本充分的依据，这不构成有效的统计论证。此次验收只确认流程和数值一致，不确认样本充分、算法收敛或科研结论。单个合成数据、单次运行不能代表真实脑数据效果或算法优劣。

## 2026-11-15：Docker 验收

镜像构建、导出、SHA-256 校验和重新导入通过。独立 CPU 容器内 pip check 正常，9 项核心测试通过。NOTEARS、GOLEM、DAG-GNN 的固定脚本小样例 3/3 成功。实际 Pi 任务 exp_f17ae4e75b6b4e33 的 7 次工具调用全部成功，NOTEARS CPU 耗时 2.291871 秒，F1=1、SHD=0。已独立核对预测矩阵、真值及运行 manifest。标准桥接安装和本机代理 host 网络安装均启动成功。详见 docker-release-20261115.md。

## 尚未验证

- GPU容器执行、跨机器安装。已验证同一服务器上使用独立数据目录的新CPU容器，不依赖Conda；这不等同于全新操作系统验证。
- Agent多任务成功率、失败恢复的真实模型测试及Agent基线比较。单个真实模型任务已通过，见上节。
- 真实脑数据输入示例。当前运行使用明确标记的合成数据，用户尚未提供真实脑区时序。
- 正式科研规模的多条件、多数据实例比较及收敛分析。
- 用户的最终安装与OBS录屏。
- 至少1位外部使用者验证。不能用开发者自测或作者自行录屏代替。

原生环境测试不等同于容器安装测试，工具接口测试不等同于真实模型端到端测试。
