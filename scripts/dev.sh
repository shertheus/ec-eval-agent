#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$task_root/backend${PYTHONPATH:+:$PYTHONPATH}"
export BRAIN_EVAL_WORKSPACE="${BRAIN_EVAL_WORKSPACE:-$task_root/workspace}"
export BRAIN_EVAL_INPUT="${BRAIN_EVAL_INPUT:-$task_root/input}"
task_gpu=0
if [ -f "$task_root/.runtime/gpu" ]; then read -r task_gpu < "$task_root/.runtime/gpu"; fi
export BRAIN_EVAL_GPU="${BRAIN_EVAL_GPU:-$task_gpu}"
task_python="${BRAIN_EVAL_PYTHON:-$task_root/.runtime/python}"
task_node="${BRAIN_EVAL_NODE:-$task_root/.runtime/node}"
mkdir -p "$BRAIN_EVAL_WORKSPACE" "$BRAIN_EVAL_INPUT"
case "${1:-doctor}" in
  serve) exec "$task_python" -m uvicorn brain_eval.server:app --host 127.0.0.1 --port "${BRAIN_EVAL_PORT:-8765}" ;;
  test) cd "$task_root"; exec "$task_python" -m unittest discover -s tests -v ;;
  chat) shift; exec "$task_node" --env-file="$task_root/config/deepseek.env" "$task_root/scripts/pi-entry.mjs" "$@" ;;
  *) exec "$task_python" -m brain_eval.cli "$@" ;;
esac
