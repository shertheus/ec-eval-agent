# Build on Linux x86_64; the runtime also supports CPU-only installation.
FROM node:22.22.1-bookworm-slim AS node
FROM python:3.11.10-slim-bookworm
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
ARG DEBIAN_MIRROR=http://deb.debian.org
ARG PYPI_INDEX_URL=https://pypi.org/simple
ARG NPM_REGISTRY=https://registry.npmjs.org
RUN sed -i "s|http://deb.debian.org|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::Retries=3 update && apt-get install -y --no-install-recommends libgomp1 ca-certificates git \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
COPY backend/requirements.lock.txt /app/backend/requirements.lock.txt
RUN python -m pip install --no-cache-dir torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128 \
 && python -m pip install --no-cache-dir --index-url "$PYPI_INDEX_URL" -r /app/backend/requirements.lock.txt
COPY agent/package.json agent/package-lock.json /app/agent/
RUN cd /app/agent && npm ci --registry="$NPM_REGISTRY" --ignore-scripts --no-audit --no-fund
COPY backend /app/backend
COPY agent/extensions /app/agent/extensions
COPY agent/skills /app/agent/skills
COPY scripts /app/scripts
COPY examples /app/examples
COPY LICENSE THIRD_PARTY_NOTICES.md /app/
ENV PYTHONPATH=/app/backend PYTHONUNBUFFERED=1 CASTLE_BACKEND=pytorch \
    BRAIN_EVAL_WORKSPACE=/work BRAIN_EVAL_INPUT=/input BRAIN_EVAL_GPU=0 \
    PI_CODING_AGENT_DIR=/pi-state HOME=/pi-state BRAIN_EVAL_PORT=8765 \
    NO_PROXY=127.0.0.1,localhost,::1
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:'+os.environ['BRAIN_EVAL_PORT']+'/v1/health',timeout=3)"
CMD ["sh", "-c", "exec python -m uvicorn brain_eval.server:app --host 127.0.0.1 --port \"$BRAIN_EVAL_PORT\""]
