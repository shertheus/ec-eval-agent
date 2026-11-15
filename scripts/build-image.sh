#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$task_root"
docker build -f docker/Dockerfile -t brain-eval:0.1.0 "$@" .
mkdir -p dist
docker save brain-eval:0.1.0 | gzip -1 > dist/brain-eval-image.tar.gz.tmp
mv dist/brain-eval-image.tar.gz.tmp dist/brain-eval-image.tar.gz
cd dist
sha256sum brain-eval-image.tar.gz > brain-eval-image.tar.gz.sha256
docker image inspect brain-eval:0.1.0 --format '{{.Id}}' > image-id.txt
cp ../install.sh ../install-local-proxy.sh ../brain-eval ../LICENSE ../THIRD_PARTY_NOTICES.md .
cp ../docs/docker-quickstart.md README.md
mkdir -p config
cp ../config/deepseek.env.example config/
