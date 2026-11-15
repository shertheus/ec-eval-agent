# 参考文献与使用位置

核对日期：2026-11-15。共 15 条，按规范的 ≥2023 口径计，近期条目为 9 条（60%）。已核对原始来源的题名、作者、年份与摘要；Friston 综述另核对定义段落。作者根据实际论述选择引用并阅读相关原文。

## 编号清单

[1] Friston K J. Functional and Effective Connectivity: A Review. Brain Connectivity, 1(1), 2011. https://doi.org/10.1089/brain.2011.0008
[2] Zheng X, Aragam B, Ravikumar P, Xing E P. DAGs with NO TEARS: Continuous Optimization for Structure Learning. NeurIPS 2018, 2018. https://arxiv.org/abs/1803.01422
[3] Ng I, Ghassami A, Zhang K. On the Role of Sparsity and DAG Constraints for Learning Linear DAGs. NeurIPS 2020, 2020. https://arxiv.org/abs/2006.10201
[4] Yu Y, Chen J, Gao T, Yu M. DAG-GNN: DAG Structure Learning with Graph Neural Networks. ICML 2019, 2019. https://arxiv.org/abs/1904.10098
[5] Tank A, Covert I, Foti N, Shojaie A, Fox E. Neural Granger Causality. arXiv:1802.05842; accepted revision 2021, 2018. https://arxiv.org/abs/1802.05842
[6] Zhang K, Zhu S, Kalander M, et al.. gCastle: A Python Toolbox for Causal Discovery. arXiv:2111.15155, 2021. https://arxiv.org/abs/2111.15155
[7] Schick T, Dwivedi-Yu J, Dessì R, et al.. Toolformer: Language Models Can Teach Themselves to Use Tools. arXiv:2302.04761, 2023. https://arxiv.org/abs/2302.04761
[8] Wu Q, Bansal G, Zhang J, et al.. AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation. arXiv:2308.08155, 2023. https://arxiv.org/abs/2308.08155
[9] Liu X, Yu H, Zhang H, et al.. AgentBench: Evaluating LLMs as Agents. arXiv:2308.03688; published ICLR 2024, 2023. https://arxiv.org/abs/2308.03688
[10] Jimenez C E, Yang J, Wettig A, et al.. SWE-bench: Can Language Models Resolve Real-World GitHub Issues?. arXiv:2310.06770; published ICLR 2024, 2023. https://arxiv.org/abs/2310.06770
[11] Yao S, Shinn N, Razavi P, Narasimhan K. tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains. arXiv:2406.12045, 2024. https://arxiv.org/abs/2406.12045
[12] Xie T, Zhang D, Chen J, et al.. OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments. arXiv:2404.07972, 2024. https://arxiv.org/abs/2404.07972
[13] Xia C S, Deng Y, Dunn S, Zhang L. Agentless: Demystifying LLM-based Software Engineering Agents. arXiv:2407.01489, 2024. https://arxiv.org/abs/2407.01489
[14] Lu C, Lu C, Lange R T, Foerster J, Clune J, Ha D. The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery. arXiv:2408.06292, 2024. https://arxiv.org/abs/2408.06292
[15] Wang X, Chen Y, Yuan L, et al.. Executable Code Actions Elicit Better LLM Agents. ICML 2024, 2024. https://arxiv.org/abs/2402.01030

## 与项目的对应关系

| 编号 | 可支持的内容 |
|---|---|
| [1] | 区分功能连接与效应连接；核对建模假设。 |
| [2] | NOTEARS 的连续优化与无环约束来源。 |
| [3] | GOLEM 的似然目标、稀疏性与 DAG 约束来源。 |
| [4] | DAG-GNN 的图结构学习模型来源。 |
| [5] | 非线性 Granger 与稀疏神经网络方法来源；年份按初版预印本记录。 |
| [6] | 合成数据、因果发现与图评价工具箱的集成依据。 |
| [7] | 模型选择 API、构造参数和使用工具结果的研究背景。 |
| [8] | 对话编排框架的候选设计背景；本项目采用单 Agent 与独立后端。 |
| [9] | 交互任务评价、任务成功和失败原因分析的背景。 |
| [10] | 将真实软件任务转化为可执行验证的研究背景。 |
| [11] | 比较对话结束后的真实状态与目标状态，并区分单次完成和多次可靠性。 |
| [12] | 独立初始环境与执行结果判定的评测设计背景。 |
| [13] | 讨论简单固定流程作为对照的价值；本文方法仍使用 LLM，本项目无 AI 基线为自编脚本。 |
| [14] | 科研流程自动化背景；可与本项目聚焦实验执行和证据管理的范围比较。 |
| [15] | 可执行代码动作与预定义 API 工具的接口设计比较。 |

预印本条目按初版年份列示，已确认的会议发表信息另标注；引用正式出版版时，应统一作者、题名、出版年与 DOI。项目采用 Pi 与 LangGraph 的能力比较来源为官方文档，见 docs/technical-selection.md。
