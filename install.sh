#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd "$(dirname "$0")" && pwd)"
cd "$task_root"
task_image="${BRAIN_EVAL_IMAGE:-brain-eval:0.1.0}"
task_container="${BRAIN_EVAL_CONTAINER:-brain-eval}"
task_gpu="${BRAIN_EVAL_GPU:-none}"
task_network="${BRAIN_EVAL_NETWORK:-bridge}"
task_port="${BRAIN_EVAL_PORT:-8765}"
command -v docker >/dev/null || { echo 'Docker尚未安装。CPU模式只需Docker，GPU模式另需NVIDIA Container Toolkit。'; exit 1; }
docker info >/dev/null 2>&1 || { echo '当前账户无法连接Docker，请检查服务与权限。'; exit 1; }
[[ "$task_network" == bridge || "$task_network" == host ]] || { echo 'BRAIN_EVAL_NETWORK只能为bridge或host。'; exit 1; }
[[ "$task_port" =~ ^[0-9]+$ ]] && ((task_port>=1024 && task_port<=65535)) || { echo 'BRAIN_EVAL_PORT必须为1024—65535。'; exit 1; }
if [[ "$task_network" == host ]] && command -v ss >/dev/null && [[ -n "$(ss -H -ltn "sport = :$task_port")" ]]; then
  echo "本机端口 $task_port 已占用。请设置空闲的BRAIN_EVAL_PORT，本次未安装。"
  exit 1
fi
if ! docker image inspect "$task_image" >/dev/null 2>&1; then
  if [ -f brain-eval-image.tar.gz ] && [ -f brain-eval-image.tar.gz.sha256 ]; then
    sha256sum -c brain-eval-image.tar.gz.sha256
    docker load -i brain-eval-image.tar.gz
  else
    echo '未找到交付镜像。开发者可运行 bash scripts/build-image.sh；安装用户请获取镜像包。'
    exit 1
  fi
fi
if docker container inspect "$task_container" >/dev/null 2>&1; then
  echo "容器 $task_container 已存在，本次未安装。请使用原安装目录，或指定新的BRAIN_EVAL_CONTAINER。"
  exit 1
fi
mkdir -p workspace input pi-state config
if [ ! -f config/deepseek.env ]; then
  cp config/deepseek.env.example config/deepseek.env
  chmod 600 config/deepseek.env
fi
task_options=(--network "$task_network")
if [[ "$task_gpu" != none ]]; then
  task_options+=(--gpus "device=$task_gpu")
fi
docker run -d --init --name "$task_container" --restart unless-stopped \
  --user "$(id -u):$(id -g)" "${task_options[@]}" \
  -e "BRAIN_EVAL_PORT=$task_port" -e "BRAIN_EVAL_URL=http://127.0.0.1:$task_port" \
  -v "$task_root/workspace:/work" -v "$task_root/input:/input:ro" -v "$task_root/pi-state:/pi-state" \
  -v "$task_root/config:/config:ro" \
  "$task_image" >/dev/null
printf '%s\n' "$task_container" > .container-name
for ((attempt=0;attempt<30;attempt++)); do
  if docker exec "$task_container" python -c "import urllib.request,os; urllib.request.urlopen(os.environ['BRAIN_EVAL_URL']+'/v1/health',timeout=2)" >/dev/null 2>&1; then
    chmod +x brain-eval
    echo '安装成功。./brain-eval doctor 检查环境，./brain-eval demo 运行小样例，./brain-eval 进入Pi。'
    exit 0
  fi
  sleep 1
done
echo "容器启动未通过检查，请查看 docker logs $task_container。保留容器便于诊断。"
exit 1
