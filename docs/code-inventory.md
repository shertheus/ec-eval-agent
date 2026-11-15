# 原创代码与功能清单

统计日期：2026-11-15。原创 Python 后端包含 **1,031 行有效代码、67 个函数、15 个非空 Python 模块文件**。系统级要求的代码门槛为 800 行、模块不少于 3 个，当前规模已达到要求。

## 统计方法

```bash
python scripts/count_code.py
```

脚本使用 Python AST 识别文档字符串，使用 tokenize 识别代码行。统计对象是 `backend/brain_eval/` 下的原创 Python 文件；移除空行、注释和文档字符串，不计 `vendor/`、第三方依赖、测试、基准脚本、TypeScript 扩展、Shell 安装脚本与文档。多条语句位于同一物理行时计为一行。

完整逐文件结果见 [code-inventory.json](../examples/reports/system-eval/code-inventory.json)。此口径可以直接从源码复算。

## 模块职责

| 业务模块 | 源码 | 工作内容 |
|---|---|---|
| 数据与输入协议 | contracts.py、datasets.py、protocols.py | 输入检查、数据快照、参数规范化、协议哈希 |
| 实验执行 | experiments.py、storage.py、worker.py | 持久化状态、算法子进程、超时、取消与重试 |
| 算法与评价 | adapters.py、compat.py、metrics.py | 五种方法适配、兼容处理、有向图指标 |
| 分析与交付 | reports.py、analysis_tools.py、bundles.py | 汇总、可视化、数据检查、实验对比、证据归档 |
| 服务入口 | server.py、cli.py | HTTP API、固定脚本和命令行 |

## 可验证功能

| 功能 | 入口或证据 |
|---|---|
| 1. SEM 合成数据 | prepare_dataset / datasets.py |
| 2. VAR 与 tanh 时序生成 | prepare_dataset / datasets.py |
| 3. CSV/NPY 导入与质量校验 | dataset / test_import_rejects_path_escape_and_nan |
| 4. 数据节点统计 | inspect-data / test_statistics_and_tampered_observations |
| 5. 参数和输入语义校验 | validate_protocol / test_parameter_validation |
| 6. 幂等提交 | submit_experiment / test_idempotency_and_explicit_retry |
| 7. 持久化队列与独立进程 | Scheduler / integration_test.py |
| 8. 运行状态与日志查询 | status、logs / inspect_experiment |
| 9. 取消任务 | cancel / integration_test.py |
| 10. 超时与失败保留 | timeout_seconds / 系统评测 T10 |
| 11. 按原协议重试 | retry / test_idempotency_and_explicit_retry |
| 12. 五种算法统一适配 | adapters.py / 系统评测 T01–T05 |
| 13. 有向图指标 | metrics.py / test_reversal_and_bidirectional_metrics |
| 14. 跨种子汇总与稳定性 | reports.py / integration_test.py |
| 15. CSV/JSON/SVG/HTML 报告 | results / 系统评测成功任务 |
| 16. 匹配数据的跨实验对比 | compare / test_comparison_requires_matching_data |
| 17. 文件校验与证据 ZIP | export / test_export_has_verifiable_manifest_and_no_raw_data |
| 18. Pi 自然语言入口 | 11 个领域工具 / 真实模型系统评测 |
| 19. Docker 安装与运行管理 | install.sh、brain-eval / Docker 验收记录 |

新增功能用于减少数据核对、实验整理和结果交付的手工步骤。代码规模已达标，后续开发优先改善使用流程与可复现性。
