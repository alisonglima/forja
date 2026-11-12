#!/usr/bin/env bash
# L-PROVA-KIT-00: cria, usa e destroi UM LXC descartavel no PVE.
# Sem flag = --dry-run (nenhuma chamada externa). --run e opt-in explicito.
# Contrato: tests/prova_kit/test_lxc_descartavel.py (plano/ciclo) e
#           tests/prova_kit/test_lxc_script_seguro.py (travas).
set -euo pipefail

MODO=dry-run
CTID=920
OUT=.work/prova-kit/evidencias
TEMPLATE='local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst'
STORAGE=vmdata
ROOTFS=vmdata:16
MARC=''
PVE_HOST=${PVE_HOST:-root@192.168.88.32}
KIT_TAR=${KIT_TAR:-/tmp/prova-kit.tar.gz}
EVID_TAR=''
EXPORTS=''
FASE_CMD=${FASE_CMD:-}

uso() { echo "uso: $0 [--dry-run|--run|--inside] [--ctid N] [--out DIR]" >&2; }
erro() { echo "erro: $*" >&2; }

# Valida antes de criar diretorio, gravar arquivo ou chamar qualquer coisa.
validar_ctid() {
  case "$1" in
    ''|*[!0-9]*) erro "ctid invalido: '$1' (inteiro positivo)"; exit 2 ;;
  esac
  if [ "$1" -eq 219 ]; then erro "CT 219 e referencia, nunca destino"; exit 2; fi
  if [ "$1" -eq 0 ]; then erro "ctid invalido: '$1' (inteiro positivo)"; exit 2; fi
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) MODO=dry-run; shift ;;
    --run)     MODO=run; shift ;;
    --inside)  MODO=inside; shift ;;
    --ctid)    [ $# -ge 2 ] || { erro "--ctid exige valor"; exit 2; }; CTID=$2; shift 2 ;;
    --out)     [ $# -ge 2 ] || { erro "--out exige valor"; exit 2; }; OUT=$2; shift 2 ;;
    -h|--help) uso; exit 0 ;;
    *)         erro "argumento desconhecido: $1"; uso; exit 2 ;;
  esac
done

# Roda dentro do CT (nunca chama ssh/pct). Ordem fixa; nao para na primeira falha.
modo_inside() {
  local raiz=${INSIDE_ROOT:-/srv/prova}
  local fases=(export-exato export-pdf preflight-provocado lote-csv video-compare medir-rede)
  local fase alvo rc falhou=0 primeiro=1 json='['
  mkdir -p "$raiz/evidencias"
  for fase in "${fases[@]}"; do
    alvo="$raiz/scripts/prova-kit/$fase.mjs"
    [ -f "$alvo" ] || continue
    rc=0
    node "$alvo" --out "$raiz/evidencias" || rc=$?
    [ "$rc" -eq 0 ] || falhou=1
    if [ "$primeiro" -eq 1 ]; then primeiro=0; else json+=','; fi
    json+="{\"fase\": \"$fase\", \"exit\": $rc}"
  done
  json+=']'
  printf '%s\n' "$json" > "$raiz/evidencias/fases.json"
  [ "$falhou" -eq 0 ]
}

if [ "$MODO" = inside ]; then
  if modo_inside; then exit 0; else exit 1; fi
fi

validar_ctid "$CTID"
KIT_TAR="/tmp/prova-kit-$CTID.tar.gz"
EVID_TAR="/tmp/evidencias-$CTID.tar.gz"
HOSTNAME="prova-kit-$CTID"
MARC="forja-prova-kit-$CTID-$(date -u +%Y%m%dT%H%M%SZ)"
data_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# Plano unico: ID livre -> create -> start/exec -> pull -> destroy --purge ->
# pct status final. Todo comando pct create carrega o marcador.
montar_comandos() {
  CMD_ID="pct status $CTID || qm status $CTID"
  CMD_CREATE="pct create $CTID '$TEMPLATE' --hostname $HOSTNAME --cores 4 --memory 6144 --swap 1024 --rootfs '$ROOTFS' --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1 --onboot 0 --description '$MARC'"
  CMD_START="pct start $CTID"
  CMD_PUSH="pct push $CTID $KIT_TAR /srv/prova/prova-kit.tar.gz"
  CMD_EXEC="pct exec $CTID -- bash -lc 'cd /srv/prova && tar xzf prova-kit.tar.gz && INSIDE_ROOT=/srv/prova bash scripts/prova-kit/lxc-descartavel.sh --inside'"
  CMD_PULL="pct pull $CTID /srv/prova/evidencias.tar.gz $EVID_TAR"
  CMD_SHA="sha256sum $EVID_TAR"
  CMD_DESTROY="pct stop $CTID || true; pct destroy $CTID --purge"
  CMD_STATUS="pct status $CTID"
}

escrever_plano() {
  python3 - "$OUT/lxc-plano.json" "$CTID" "$TEMPLATE" "$ROOTFS" "$HOSTNAME" \
    "$MARC" "$CMD_ID" "$CMD_CREATE" "$CMD_START" "$CMD_PUSH" "$CMD_EXEC" \
    "$CMD_PULL" "$CMD_SHA" "$CMD_DESTROY" "$CMD_STATUS" <<'PY'
import json, sys
p = {"dry_run": True, "ctid": int(sys.argv[2]), "template": sys.argv[3],
     "rootfs": sys.argv[4], "hostname": sys.argv[5], "cores": 4,
     "memoria_mb": 6144, "swap_mb": 1024, "unprivileged": True,
     "nesting": True, "marcador": sys.argv[6], "comandos": sys.argv[7:]}
txt = json.dumps(p, indent=2, ensure_ascii=False)
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    fh.write(txt + "\n")
sys.stdout.write(txt + "\n")
PY
}

# ---------- modo --run (o orquestrador executa; esta lane nao roda) ----------
SSH_OPTS='-o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10'
ssh_pve() { ssh $SSH_OPTS "$PVE_HOST" "$@"; }
CRIADO=0
DESTRUIDO=0
INICIO=''
FIM=''
SHA_LOCAL=''
SHA_CT=''
ST_EXIT=0
ST_EXISTE=false
TEMPLATE_RUN=''
ROOTFS_RUN=''

sha_local() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

puxar_erro() {
  if ssh_pve "pct pull $CTID /srv/prova/erro.json /tmp/erro-$CTID.json" >/dev/null 2>&1; then
    ssh_pve "cat /tmp/erro-$CTID.json" > "$OUT/erro.json" 2>/dev/null || true
  fi
}

confirmar_marcador() {
  local cfg
  cfg=$(ssh_pve "pct config $CTID" 2>/dev/null) || return 1
  case "$cfg" in *"$MARC"*) ;; *) return 1 ;; esac
  case "$cfg" in *"hostname: $HOSTNAME"*) return 0 ;; esac
  return 1
}

destruir() {
  if confirmar_marcador; then
    ssh_pve "pct stop $CTID || true; pct destroy $CTID --purge"
  else
    erro "config do CT $CTID sem marcador/hostname; nao destruo"
    return 1
  fi
}

cleanup() {
  local rc=$?
  trap - EXIT
  set +e
  if [ "$CRIADO" -eq 1 ] && [ "$DESTRUIDO" -eq 0 ]; then
    puxar_erro
    if destruir >/dev/null; then DESTRUIDO=1; fi
  fi
  ssh_pve "rm -f /tmp/prova-kit-$CTID.tar.gz /tmp/evidencias-$CTID.tar.gz /tmp/erro-$CTID.json" >/dev/null 2>&1 || true
  exit "$rc"
}

escrever_ciclo() {
  python3 - "$OUT/lxc-ciclo.json" "$CTID" "$TEMPLATE_RUN" "$ROOTFS_RUN" \
    "$INICIO" "$FIM" "$1" "$SHA_LOCAL" "$SHA_CT" "$ST_EXIT" "$ST_EXISTE" <<'PY'
import json, sys
c = {"ctid": int(sys.argv[2]), "template": sys.argv[3], "rootfs": sys.argv[4],
     "inicio": sys.argv[5], "fim": sys.argv[6], "destroy_ok": sys.argv[7] == "true",
     "sha256": {"local": sys.argv[8], "ct": sys.argv[9]},
     "pct_status_final": {"exit_code": int(sys.argv[10]),
                          "existe": sys.argv[11] == "true"}}
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(c, fh, indent=2)
    fh.write("\n")
PY
}

# Provisao da base no CT (K.1 passos 2 e 3). Versoes vao para ambiente.json.
fase_base() {
  local script ns='' sb=false
  if [ "${CHROME_NO_SANDBOX:-0}" = 1 ]; then ns='--no-sandbox '; sb=true; fi
  script=$(cat <<'BASE'
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl xz-utils gnupg jq poppler-utils imagemagick qpdf tcpdump time ffmpeg fonts-dejavu-core fonts-liberation
curl -fsSL -o /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get install -y /tmp/chrome.deb
google-chrome --version
curl -fsSL -o /tmp/nodesource_setup.sh https://deb.nodesource.com/setup_22.x
NODE_SHA=$(sha256sum /tmp/nodesource_setup.sh | awk '{print $1}')
echo "nodesource sha256: $NODE_SHA"
bash /tmp/nodesource_setup.sh
apt-get install -y nodejs
node --version
npx --yes @feimacode/open-design-agent-kit@0.4.0 --help > /srv/prova/evidencias/kit-help.txt
npm view @feimacode/open-design-agent-kit@0.4.0 dist.integrity
printf '%s\n' '#!/bin/sh' \
  'exec /usr/bin/google-chrome-stable \' \
  '  --disable-background-networking --disable-component-update --disable-default-apps \' \
  '  --disable-sync --no-first-run --no-default-browser-check --metrics-recording-only \' \
  '  --disable-dev-shm-usage --disable-features=Translate,OptimizationHints,MediaRouter \' \
  '  __NS__--host-resolver-rules="MAP * ~NOTFOUND , EXCLUDE localhost , EXCLUDE 127.0.0.1" "$@"' \
  > /usr/local/bin/google-chrome-prova
chmod 0755 /usr/local/bin/google-chrome-prova
if [ -x /usr/bin/google-chrome-stable ]; then /usr/local/bin/google-chrome-prova --version; fi
# Sanidade (2a execucao real: o wrapper bloqueava 127.0.0.1 e toda prova renderizou "This site can't be reached"):
# o Chrome da prova TEM de alcancar o loopback (o kit serve o artefato por 127.0.0.1) e NAO a internet.
if [ -x /usr/bin/google-chrome-stable ]; then
  node -e "require('http').createServer((q,r)=>r.end('<p id=\"ok\">loopback</p>')).listen(38765,'127.0.0.1')" &
  SRV_LOOP=$!
  sleep 2
  /usr/local/bin/google-chrome-prova --headless --dump-dom http://127.0.0.1:38765/ > /srv/prova/evidencias/chrome-loopback.txt 2>/dev/null || true
  /usr/local/bin/google-chrome-prova --headless --dump-dom http://example.com/ > /srv/prova/evidencias/chrome-externo.txt 2>/dev/null || true
  kill "$SRV_LOOP" 2>/dev/null || true
  grep -q 'id="ok"' /srv/prova/evidencias/chrome-loopback.txt || { echo "ERRO: o Chrome da prova nao alcanca 127.0.0.1" >&2; exit 1; }
  if grep -qi 'example domain' /srv/prova/evidencias/chrome-externo.txt; then echo "ERRO: o Chrome da prova alcanca a internet" >&2; exit 1; fi
fi
CHROME_VER=$(google-chrome --version 2>/dev/null || echo desconhecido)
NODE_VER=$(node --version 2>/dev/null || echo desconhecido)
KIT_VER=$(npm view @feimacode/open-design-agent-kit@0.4.0 version 2>/dev/null | tail -n1 || echo desconhecido)
KIT_INTEG=$(npm view @feimacode/open-design-agent-kit@0.4.0 dist.integrity 2>/dev/null | tail -n1 || echo desconhecido)
{
  printf '{\n'
  printf '  "chrome": "%s",\n' "$CHROME_VER"
  printf '  "node": "%s",\n' "$NODE_VER"
  printf '  "kit": "%s",\n' "$KIT_VER"
  printf '  "kit_integrity": "%s",\n' "$KIT_INTEG"
  printf '  "sha256_nodesource": "%s",\n' "$NODE_SHA"
  printf '  "no_sandbox": __SB__\n'
  printf '}\n'
} > /srv/prova/evidencias/ambiente.json
BASE
)
  script=${script//__NS__/$ns}
  script=${script//__SB__/$sb}
  ssh_pve "pct exec $CTID -- bash -lc $(printf '%q' "$script")"
}

montar_exports() {
  EXPORTS='export OPEN_DESIGN_BROWSER_PATH=/usr/local/bin/google-chrome-prova; '
  EXPORTS+='export OPEN_DESIGN_WORKSPACE_ROOT=/srv/prova/workspace; '
  EXPORTS+='export OPEN_DESIGN_DEFAULT_WORKSPACE=/srv/prova/workspace; '
  EXPORTS+='export OPEN_DESIGN_OUTPUT_DIR=/srv/prova/out; '
  EXPORTS+='export OPEN_DESIGN_PREVIEW=off; '
  EXPORTS+='export OPEN_DESIGN_FFMPEG_PATH=/usr/bin/ffmpeg; '
  EXPORTS+='unset OPEN_DESIGN_FIGMA_TOKEN; '
  EXPORTS+='test ! -e /root/.config/open-design/integrations.json && '
}

rodar_inside() {
  local script="cd /srv/prova && tar xzf prova-kit.tar.gz && ${EXPORTS}INSIDE_ROOT=/srv/prova bash scripts/prova-kit/lxc-descartavel.sh --inside"
  [ -z "$FASE_CMD" ] || script="cd /srv/prova && tar xzf prova-kit.tar.gz && ${EXPORTS}${FASE_CMD}"
  ssh_pve "pct exec $CTID -- bash -lc $(printf '%q' "$script")"
}

empacotar_kit() {
  local raiz
  local itens=(scripts/prova-kit)
  raiz=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
  if [ -f "$raiz/remotion-template/package.json" ]; then itens+=(remotion-template/package.json); fi
  if [ -d "$raiz/remotion-template/src" ]; then itens+=(remotion-template/src); fi
  tar czf "$OUT/prova-kit.tar.gz" -C "$raiz" "${itens[@]}"
}

if [ "$MODO" = dry-run ]; then
  mkdir -p "$OUT"
  montar_comandos
  escrever_plano
  exit 0
fi

# --run: a partir daqui ha rede/PVE. Nunca reutiliza CT existente.
mkdir -p "$OUT"
trap cleanup EXIT
if ! STATUS_TOKEN=$(ssh_pve "if pct status $CTID >/dev/null 2>&1 || qm status $CTID >/dev/null 2>&1; then echo EXISTE; else echo LIVRE; fi"); then
  erro "ssh/PVE falhou ao consultar o CT/VM $CTID"; exit 1
fi
case "$STATUS_TOKEN" in
  LIVRE) ;;
  EXISTE) erro "CT/VM $CTID ja existe; preservar e usar outro id"; exit 2 ;;
  *) erro "resposta inesperada do ssh/PVE para o CT/VM $CTID: '$STATUS_TOKEN'"; exit 1 ;;
esac

TEMPLATE_RUN=$(ssh_pve "pveam list local | awk '/debian-13-standard/{print \$1; exit}'" 2>/dev/null | tr -d '\r' || true)
if [ -z "$TEMPLATE_RUN" ]; then
  TEMPLATE_RUN=$(ssh_pve "pveam list local | awk '/debian-12-standard/{print \$1; exit}'" 2>/dev/null | tr -d '\r' || true)
fi
[ -n "$TEMPLATE_RUN" ] || { erro "template Debian 13/12 ausente no PVE"; exit 1; }
STORAGE=$(ssh_pve "pvesm status -content rootdir | awk 'NR>1{print \$1; exit}'" 2>/dev/null | tr -d '\r' || true)
[ -n "$STORAGE" ] || STORAGE=vmdata
ROOTFS_RUN="$STORAGE:16"
TEMPLATE=$TEMPLATE_RUN
ROOTFS=$ROOTFS_RUN
montar_comandos
escrever_plano >/dev/null

INICIO=$(data_utc)
ssh_pve "$CMD_CREATE" || { erro "pct create falhou"; exit 1; }
CRIADO=1
ssh_pve "$CMD_START" || { erro "pct start falhou"; exit 1; }
i=0
while [ "$i" -lt 30 ]; do
  ssh_pve "pct exec $CTID -- ip -4 -o addr show eth0" 2>/dev/null | grep -q 'inet ' && break
  i=$((i + 1)); sleep 2
done
empacotar_kit || { erro "empacotar kit falhou"; exit 1; }
ssh_pve "cat > $KIT_TAR" < "$OUT/prova-kit.tar.gz" || { erro "envio do kit falhou"; exit 1; }
ssh_pve "pct exec $CTID -- mkdir -p /srv/prova/evidencias /srv/prova/workspace /srv/prova/out /usr/local/bin" >/dev/null || { erro "mkdir no CT falhou"; exit 1; }
ssh_pve "$CMD_PUSH" >/dev/null || { erro "pct push falhou"; exit 1; }
fase_base || { erro "provisao da base falhou"; exit 1; }
montar_exports
FASE_RC=0
rodar_inside || { FASE_RC=$?; erro "fase do kit falhou (exit $FASE_RC); trago as evidencias antes de destruir"; }
ssh_pve "pct exec $CTID -- tar czf /srv/prova/evidencias.tar.gz -C /srv/prova evidencias" >/dev/null || { erro "tar das evidencias falhou"; exit 1; }
ssh_pve "$CMD_PULL" >/dev/null || { erro "pct pull falhou"; exit 1; }
ssh_pve "cat $EVID_TAR" > "$OUT/evidencias-$CTID.tar.gz" || { erro "evidencias nao chegaram ao Mac"; exit 1; }
SHA_LOCAL=$(sha_local "$OUT/evidencias-$CTID.tar.gz")
SHA_CT=$(ssh_pve "pct exec $CTID -- sha256sum /srv/prova/evidencias.tar.gz" | awk '{print $1}' | tr -d '\r' || true)
ssh_pve "rm -f $KIT_TAR $EVID_TAR" >/dev/null || true
if [ -z "$SHA_CT" ] || [ "$SHA_LOCAL" != "$SHA_CT" ]; then
  erro "sha256 divergente entre Mac e CT para o CT $CTID"; exit 1
fi
FIM=$(data_utc)
[ "$FASE_RC" -eq 0 ] || { erro "evidencias parciais gravadas em $OUT/evidencias-$CTID.tar.gz (fase exit $FASE_RC)"; exit 1; }

DESTRUIDO=0
if destruir; then DESTRUIDO=1; CRIADO=0; fi
ST_OUT=$(ssh_pve "pct status $CTID 2>&1" || true)
case "$ST_OUT" in
  *"status: running"*|*"status: stopped"*) ST_EXISTE=true; ST_EXIT=0 ;;
  *) ST_EXISTE=false; ST_EXIT=1 ;;
esac
if [ "$DESTRUIDO" -eq 1 ] && [ "$ST_EXISTE" = false ]; then
  escrever_ciclo true
  exit 0
fi
escrever_ciclo false
erro "destroy/final status inconsistente para o CT $CTID"
exit 1
