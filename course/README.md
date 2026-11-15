# 课程交付材料索引

项目采用实践轨，按系统级目标准备。代码与软件验收对应版本 0.2.0、提交 b551585；本目录补充提交材料、图表与核对工具。技术材料由 AI 协助整理，供作者核验后组织个人说明。

主报告使用 Markdown：[实践说明](实践说明.md)。架构与图表采用可编辑 SVG。

## 已完成材料

| 内容 | 位置 | 证据 |
|---|---|---|
| 项目用途、安装、运行与已知问题 | [README](../README.md) | 具备规定的五节和可复制命令 |
| 架构与模块 | [架构说明](../docs/architecture.md) | Pi、FastAPI、调度、算法、结果管理 |
| 系统评测 | [评测报告](../docs/system-evaluation.md) | 10 任务×2入口，四项指标，失败案例 |
| 技术选型 | [选型比较](../docs/technical-selection.md) | 固定脚本、Pi、LangGraph；算法库与部署 |
| 代码量 | [代码清单](../docs/code-inventory.md) | 原创后端 1031 行；15 个非空模块文件 |
| Docker | [验收记录](../docs/docker-release-020.md) | 镜像校验、13 项容器测试、真实模型任务 |
| 参考文献 | [来源清单](references.md) | 15 条已核对元数据的研究文献，其中 9 条为 2023 年及以后 |
| 录制 | [操作稿](recording-script.md) | 安装、输入文件、运行与报告展示 |
| 提交检查 | [状态表](submission-checklist.md) | 区分已完成、待作者填写和待实际操作 |

## 最终提交的组成

按 v2.4 的实践轨条款准备 PDF 说明文档、公开代码仓库和视频链接、独立 AI 使用声明表，并保留包含 README 与可编辑图表的源文件 ZIP。文件名使用 `学号_姓名_实践.pdf`、`学号_姓名_实践_源文件.zip`、`学号_姓名_声明表.docx`。

说明文档的七个标题骨架见 [报告结构](templates/report-outline.md)。个人信息、正式封面、反思与结论、自评、签名、视频和外部验证完成后，再生成最终提交版。技术附件可先用于检查系统实现与证据。

## 复算

```bash
python scripts/count_code.py
python scripts/check_course_materials.py
```

`check_course_materials.py` 检查 README 内容、代码规模、评测矩阵和文献记录，并输出需要本人完成的项目。它不自动给课程总分，也不把空白模板认定为已完成验证。

## 图表与声明表重建

图表和声明表的构建工具需要 reportlab、python-docx；它们属于文档制作环境，独立于软件运行依赖。字体路径通过 `--font` 指定，可使用本机支持中文的 TrueType 字体。

```bash
python course/build_materials.py --kind figures --font /path/to/chinese-font.ttf
python course/build_materials.py --kind docx --output /path/to/output
```
