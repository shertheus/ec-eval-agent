# Docker 安装与录屏

此发行包面向 Linux x86_64。镜像包含 Node、Pi、Python、CUDA 12.8 版 PyTorch、gCastle 和评测后端。默认 CPU 模式仅要求 Docker 可用，不依赖宿主机 Conda。GPU 模式另需管理员安装 NVIDIA Container Toolkit。

## 录制前

解压或复制发行包到一个新的安装目录。目录应包含镜像归档、校验文件、install.sh、install-local-proxy.sh、brain-eval、config/deepseek.env.example。

先把配置模板复制为 config/deepseek.env 并填好密钥，权限设为 600。文件属于当前用户，不能放进公开发行包或录屏画面。

开发者验收使用网关模型别名 deepseek-latest-flash，deepseek-latest 在该账户下无权限。请以自己的模型服务为准。在 config/deepseek.env 中保留用户填写的密钥与接口地址，并使用下列非敏感设置：

```dotenv
DEEPSEEK_MODEL=deepseek-latest-flash
HTTP_PROXY=http://127.0.0.1:18083
HTTPS_PROXY=http://127.0.0.1:18083
NO_PROXY=127.0.0.1,localhost,::1
```

本机已有 18083 代理时，在 Mac 上保持 SSH 中转运行：

```bash
ssh -NT -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -R 127.0.0.1:18083:127.0.0.1:18083 your-server
```

your-server 是占位符，请替换为自己的 SSH 主机。已建立中转时不要重复启动。该命令不会创建本机代理本身。本机代理、Mac 和 SSH 中转都需要在线。访问公开可直连模型接口时无需这个中转，也无需代理环境变量。

## 录制时：安装 → 启动 → 任务 → 输出

在服务器的新安装目录执行：

```bash
ls
sha256sum -c brain-eval-image.tar.gz.sha256
time docker load -i brain-eval-image.tar.gz
time bash install-local-proxy.sh
./brain-eval doctor
./brain-eval
```

install-local-proxy.sh 是针对本机代理的 Linux 安装入口，使用 host 网络、回环地址 127.0.0.1:18765 和 CPU 模式，避免占用开发后端的 8765 端口。密钥由 Pi 进程从只读挂载读取，不进入镜像。标准桥接网络安装使用 bash install.sh，适用于模型服务可从容器直接访问的情况。

粘贴以下任务：

> 生成5节点、200样本的线性SEM合成数据，边数参数4，数据种子42。使用NOTEARS在CPU运行，算法种子42，max_iter=20、lambda1=0.1、w_threshold=0.3。实验标题为“Docker课程演示”。先验证协议再提交，等待完成并导出报告。给出F1、SHD、耗时和实际真值边数。这只是合成数据流程演示。

报告保存在安装目录的 workspace/experiments/<本次实验编号>/reports/report.html。Pi 返回的 /work/... 是容器内路径，在宿主机对应安装目录下的 workspace/...。可用 VS Code Remote-SSH 打开报告，或复制整个 reports 文件夹到本机后用浏览器打开，保留同目录的 SVG。

录屏建议：安装与启动约 1 分钟，输入及等待任务约 1 分钟，报告约 1 分钟。实际导入时间取决于磁盘和镜像大小；剪辑等待应注明真实耗时。预演与正式录制使用不同实验编号。若镜像已缓存，docker load 仍可验证导入，但不能声称是首次安装 Docker 引擎或在全新操作系统上安装。

## 检查与控制

```bash
./brain-eval list
./brain-eval logs
./brain-eval stop
./brain-eval start
```

安装脚本不覆盖现有同名容器。测试和正式安装使用不同目录与容器名，例如在测试目录使用 BRAIN_EVAL_CONTAINER=brain-eval-acceptance BRAIN_EVAL_PORT=18766 bash install-local-proxy.sh。不要复制开发 workspace 或旧的 .container-name 到新安装目录。

启用 GPU 时，在新安装目录中设置 BRAIN_EVAL_GPU=1 后执行安装入口。当前 CPU 演示不证明 GPU 容器已验证，GPU 启动必须先通过管理员配置的 NVIDIA 容器运行时。

Docker 安装和算法后端可以离线运行。自然语言 Agent 需要能访问已配置的模型接口。软件安装演示与至少一位外部使用者验证分别记录。
