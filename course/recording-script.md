# 三分钟安装与文件输入演示

演示以 Docker 0.2.0 的 CPU 模式为主。录制前准备模型配置、代理、镜像归档和一个独立安装目录。下列时间是镜头预算，实际等待时间按录像标注。

| 时间 | 操作 | 说明要点 |
|---|---|---|
| 0:00–0:15 | 展示仓库与项目名称 | 脑连接算法的配置、执行、评价与证据导出 |
| 0:15–0:55 | 导入镜像、执行安装入口 | Docker 已由管理员安装；当前演示项目安装 |
| 0:55–1:10 | doctor 并展示 input 下 CSV 文件 | 输入为 120×3 数值矩阵，明确标注合成示例 |
| 1:10–2:10 | 启动 Pi，粘贴下列导入任务 | 读取文件、检查统计、验证协议、提交与等待 |
| 2:10–2:45 | 展示本次报告及 ZIP 路径 | 无真值输入报告边数、耗时；保留配置与校验清单 |
| 2:45–3:00 | 展示本次实验编号与仓库链接 | 同一实验可从协议追溯到结果 |

## 安装命令

在独立交付目录执行：

```bash
sha256sum -c brain-eval-image.tar.gz.sha256
time docker load -i brain-eval-image.tar.gz
time bash install-local-proxy.sh
./brain-eval doctor
./brain-eval
```

模型可直连时改用 `bash install.sh`。密钥配置在录制前完成，不展示其内容。

## 准备文件输入

仓库提供 `course/demo-input/roi_demo.csv`、元信息和校验和。把 CSV 复制到安装目录的 `input/roi_demo.csv`。这是固定种子的合成时序，用于演示真实文件读取与处理，不属于受试者脑数据。

## 输入 Pi 的任务

> 导入 input 目录下的 roi_demo.csv，声明为 timeseries，来源写“课程演示用合成VAR时序”。检查数据形状和节点统计。使用 Granger 在 CPU 运行，lag=1、alpha=0.05，算法种子1，超时30秒。先验证再提交，等待结束，收集报告并导出证据ZIP。给出实验编号、边数、耗时和文件路径；此输入不提供结构真值。

## 打开输出

Pi 返回的 `/work/experiments/<编号>/reports/report.html` 在宿主机对应安装目录的 `workspace/experiments/<编号>/reports/report.html`。通过 Remote-SSH 打开，或复制整个 reports 目录到本机浏览器查看，保留 SVG 文件。ZIP 位于安装目录 `workspace/exports/`。

如需展示有真值的 F1/SHD，可使用 docs/docker-quickstart.md 的 SEM 生成任务。正式录制使用新实验编号，保留实际等待时间；外部使用者另填写验证记录。
