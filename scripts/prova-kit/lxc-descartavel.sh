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
FASE_CMD=${FASE_CMD:-}

uso() { echo "uso: $0 [--dry-run|--run] [--ctid N] [--out DIR]" >&2; }
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
    --ctid)    [ $# -ge 2 ] || { erro "--ctid exige valor"; exit 2; }; CTID=$2; shift 2 ;;
    --out)     [ $# -ge 2 ] || { erro "--out exige valor"; exit 2; }; OUT=$2; shift 2 ;;
    -h|--help) uso; exit 0 ;;
    *)         erro "argumento desconhecido: $1"; uso; exit 2 ;;
  esac
done

validar_ctid "$CTID"
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
  CMD_EXEC="pct exec $CTID -- bash -lc 'cd /srv/prova && tar xzf prova-kit.tar.gz'"
  CMD_PULL="pct pull $CTID /srv/prova/evidencias.tar.gz $OUT/evidencias-$CTID.tar.gz"
  CMD_SHA="sha256sum $OUT/evidencias-$CTID.tar.gz"
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
  ssh_pve "pct pull $CTID /srv/prova/erro.json '$OUT/erro.json'" >/dev/null 2>&1 || true
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
    destruir >/dev/null 2>&1 && DESTRUIDO=1
  fi
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

if [ "$MODO" = dry-run ]; then
  mkdir -p "$OUT"
  montar_comandos
  escrever_plano
  exit 0
fi

# --run: a partir daqui ha rede/PVE. Nunca reutiliza CT existente.
mkdir -p "$OUT"
trap cleanup EXIT
if ssh_pve "pct status $CTID >/dev/null 2>&1 || qm status $CTID >/dev/null 2>&1"; then
  erro "CT/VM $CTID ja existe; preservar e usar outro id"; exit 2
fi

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

INICIO=$(data_utc)
ssh_pve "$CMD_CREATE" || { erro "pct create falhou"; exit 1; }
CRIADO=1
ssh_pve "$CMD_START" || { erro "pct start falhou"; exit 1; }
i=0
while [ "$i" -lt 30 ]; do
  ssh_pve "pct exec $CTID -- ip -4 -o addr show eth0" 2>/dev/null | grep -q 'inet ' && break
  i=$((i + 1)); sleep 2
done
ssh_pve "$CMD_PUSH" >/dev/null || { erro "pct push falhou"; exit 1; }
if [ -n "$FASE_CMD" ]; then
  ssh_pve "pct exec $CTID -- bash -lc 'cd /srv/prova && tar xzf prova-kit.tar.gz && $FASE_CMD'" || { erro "fase do kit falhou"; exit 1; }
else
  ssh_pve "$CMD_EXEC" >/dev/null || { erro "unpack do kit falhou"; exit 1; }
fi
ssh_pve "pct exec $CTID -- tar czf /srv/prova/evidencias.tar.gz -C /srv/prova evidencias" >/dev/null || { erro "tar das evidencias falhou"; exit 1; }
ssh_pve "$CMD_PULL" >/dev/null || { erro "pct pull falhou"; exit 1; }
SHA_LOCAL=$(sha_local "$OUT/evidencias-$CTID.tar.gz")
SHA_CT=$(ssh_pve "pct exec $CTID -- sha256sum /srv/prova/evidencias.tar.gz" | awk '{print $1}' | tr -d '\r')
FIM=$(data_utc)

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
