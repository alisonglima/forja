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
      python3 python3-venv python3-pip ca-certificates curl tini \
    && fc-cache -f && rm -rf /var/lib/apt/lists/*

# Python: pacote forja e dependencias (faster-whisper roda em CPU/int8, sem compilar nada)
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY pyproject.toml /opt/forja/pyproject.toml
COPY forja /opt/forja/forja
RUN pip install /opt/forja

# TTS local opcional (provider piper): binario + voz pt-BR CC0/MIT, sem conta/API.
# piper-tts e GPL-3.0-or-later; o audio gerado nao herda a licenca. Ver THIRD_PARTY.md.
RUN pip install "piper-tts==1.8.0"
RUN mkdir -p /opt/piper \
    && curl -fsSL --retry 3 -o /opt/piper/pt_BR-faber-medium.onnx \
       https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx \
    && curl -fsSL --retry 3 -o /opt/piper/pt_BR-faber-medium.onnx.json \
       https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json \
    && echo "858555e3a064209c57088fe6bd70c4c3dc54d03eaa00c45d5ecaf43a33f95aa7  /opt/piper/pt_BR-faber-medium.onnx" | sha256sum -c - \
    && echo "7e694de195ae3fc36dd732c445eb04fb49b649854893cb5506b978f0d50a1d6f  /opt/piper/pt_BR-faber-medium.onnx.json" | sha256sum -c -

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
