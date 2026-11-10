# syntax=docker/dockerfile:1.7
# Imagem "forja": ffmpeg (com libass/drawtext) + Python (faster-whisper) + Node/Remotion (Chrome Headless Shell).
# Alvo: linux/amd64 (Windows/WSL2 e Linux). Em Apple Silicon roda emulado; o alvo suportado e x86_64.
FROM node:22-bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
# libs do Chrome Headless Shell (lista oficial do Remotion) + ffmpeg + fontes (libass resolve fonte via fontconfig)
RUN apt-get update && apt-get install -y --no-install-recommends \
      libnss3 libdbus-1-3 libatk1.0-0 libgbm-dev libasound2 libxrandr2 libxkbcommon-dev libxfixes3 \
      libxcomposite1 libxdamage1 libatk-bridge2.0-0 libpango-1.0-0 libcairo2 libcups2 \
      ffmpeg fonts-liberation fonts-dejavu-core fonts-noto-color-emoji \
      python3 python3-venv python3-pip ca-certificates tini \
    && fc-cache -f && rm -rf /var/lib/apt/lists/*

# Python: pacote forja e dependencias (faster-whisper roda em CPU/int8, sem compilar nada)
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY pyproject.toml /opt/forja/pyproject.toml
COPY forja /opt/forja/forja
RUN pip install /opt/forja

# Remotion: template + Chrome Headless Shell na versao pareada pelo proprio Remotion
COPY remotion-template /opt/forja/remotion
WORKDIR /opt/forja/remotion
RUN npm install --no-audit --no-fund && npx remotion browser ensure
ENV FORJA_REMOTION_DIR=/opt/forja/remotion \
    PATH=/opt/forja/remotion/node_modules/.bin:$PATH \
    HF_HOME=/models \
    FORJA_MODEL_DIR=/models \
    NODE_OPTIONS=--max-old-space-size=3072

# usuario nao-root: a imagem do Node ja traz `node` (UID 1000); /projects e /models vem de volume
RUN mkdir -p /projects /models && chown -R node:node /projects /models /opt/forja/remotion
USER node
WORKDIR /projects
ENTRYPOINT ["/usr/bin/tini", "--", "forja"]
CMD ["--help"]
