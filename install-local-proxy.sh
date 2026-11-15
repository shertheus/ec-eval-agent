#!/usr/bin/env bash
# Linux preset for a model proxy bound to the host's loopback interface.
set -euo pipefail
task_root="$(cd "$(dirname "$0")" && pwd)"
export BRAIN_EVAL_NETWORK=host
export BRAIN_EVAL_PORT="${BRAIN_EVAL_PORT:-18765}"
export BRAIN_EVAL_GPU="${BRAIN_EVAL_GPU:-none}"
exec bash "$task_root/install.sh"
