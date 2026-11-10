#!/usr/bin/env bash
# Atalhos do kit (Linux, macOS, WSL2/Git Bash). No Windows puro use kit.ps1.
set -euo pipefail
cd "$(dirname "$0")"
c() { docker compose "$@"; }
usage() { cat <<'U'
uso: ./kit.sh <comando>
  setup                 cria .env (com senha aleatoria do navegador) e a pasta projects/
  doctor                confere Docker, Compose, arquitetura, provedor de voz e espaco em disco
  build                 constroi a imagem do pipeline (a primeira vez demora alguns minutos)
  new <nome> <video>    cria projects/<nome>/ com o video e roda `forja init`
  run <args...>         roda o CLI dentro do container, ex.: ./kit.sh run --project /projects/meu qa --strict
  shell                 abre um shell no container do pipeline
  browser-up            sobe o Chromium em container (tela: https://localhost:3001; CDP so em 127.0.0.1:9222)
  browser-down          derruba o Chromium (o perfil logado fica no volume)
  browser-reset         derruba E apaga o perfil logado (revogue tambem a sessao na sua conta Google)
U
}
rand() { od -An -N18 -tx1 /dev/urandom | tr -d ' \n'; }
cmd=${1:-}; shift || true
if [ -n "$cmd" ] && [ "$cmd" != "setup" ] && [ ! -f .env ]; then bash "$0" setup >/dev/null; echo ".env criado automaticamente (a chave de API e opcional; o padrao e Google AI Studio)"; fi
case "$cmd" in
  setup)
    [ -f .env ] || cp .env.example .env
    grep -q '^BROWSER_PASSWORD=.\+' .env || { p=$(rand); sed -i.bak "s/^BROWSER_PASSWORD=.*/BROWSER_PASSWORD=$p/" .env && rm -f .env.bak; echo "senha do navegador gerada em .env"; }
    u=$(id -u 2>/dev/null || echo 1000); g=$(id -g 2>/dev/null || echo 1000); [ "$u" = 0 ] && u=1000 && g=1000
    sed -i.bak "s/^FORJA_UID=.*/FORJA_UID=$u/; s/^FORJA_GID=.*/FORJA_GID=$g/" .env && rm -f .env.bak
    chmod 600 .env 2>/dev/null || true
    mkdir -p projects models; echo "pronto. Padrao: Google AI Studio (gere as vozes e salve em voices/). Piper local e API sao opcionais." ;;
  doctor)
    docker --version; c version --short 2>/dev/null || { echo "ERRO: docker compose v2 ausente"; exit 1; }
    echo "arquitetura do daemon: $(docker info --format '{{.OSType}}/{{.Architecture}}')"
    [ -f .env ] && grep -q '^GEMINI_API_KEY=.\+' .env && echo "GEMINI_API_KEY: definida (opcional)" || echo "GEMINI_API_KEY: ausente (opcional; o padrao e o provider google_ai_studio)"
    df -h . | tail -1 ;;
  build) c build forja ;;
  new)
    [ $# -ge 2 ] || { usage; exit 2; }
    case "$1" in
      ""|.*|*..*|*[!A-Za-z0-9._-]*) echo "ERRO: nome do projeto invalido (use letras, numeros, ponto, hifen ou sublinhado; sem / nem ..)"; exit 2;;
    esac
    mkdir -p projects; cp "$2" "projects/.entrada-$1.mp4"
    c run --rm forja init "/projects/$1" --source "/projects/.entrada-$1.mp4" "${@:3}"; rm -f "projects/.entrada-$1.mp4" ;;
  run) c run --rm forja "$@" ;;
  shell) c run --rm --entrypoint bash forja ;;
  browser-up) c --profile browser up -d browser cdp-proxy; echo "tela: https://localhost:3001 (aceite o certificado) | CDP: http://127.0.0.1:9222" ;;
  browser-down) c --profile browser stop browser cdp-proxy ;;
  browser-reset) c --profile browser down -v ;;
  *) usage; exit 2 ;;
esac
