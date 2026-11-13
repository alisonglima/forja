#!/usr/bin/env bash
# CT fixo da Forja no PVE do Lab88 (padrao do setup pessoal).
#   create     cria o CT (nao refaz se existir) e o liga
#   provision  instala pacotes, Chrome, Node, venv e a Forja dentro do CT
#   keys       autoriza no CT as mesmas chaves que o PVE ja aceita (Mac, agente DSH, OCI)
#   verify     prova o CT e os tres caminhos de acesso (Mac, OCI host, agente DSH)
#   status     resumo curto
# Todo comando vai ao PVE por SSH; --dry-run so imprime. Nunca mexe em outro CT.
set -euo pipefail

CTID=${FORJA_CTID:-220}
HOSTNAME_CT=${FORJA_CT_HOSTNAME:-lab88-forja}
IP=${FORJA_CT_IP:-192.168.88.58}
GW=${FORJA_CT_GW:-192.168.88.1}
PVE_HOST=${PVE_HOST:-root@192.168.88.32}
TEMPLATE=${FORJA_TEMPLATE:-local:vztmpl/debian-12-standard_12.12-1_amd64.tar.zst}
STORAGE=${FORJA_STORAGE:-vmdata}
REPO_URL=${FORJA_REPO_URL:-https://github.com/alisonglima/forja}
BRANCH=${FORJA_BRANCH:-studio/integracao}
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=10"
NEW="-o StrictHostKeyChecking=accept-new"
DRY=0

erro() { echo "erro: $*" >&2; exit 1; }
ssh_pve() { if [ "$DRY" = 1 ]; then echo "[dry-run] ssh $PVE_HOST $*"; else ssh $SSH_OPTS "$PVE_HOST" "$@"; fi; }
in_ct() { ssh_pve "pct exec $CTID -- bash -lc $(printf '%q' "$1")"; }
existe() { ssh_pve "pct status $CTID" >/dev/null 2>&1; }

cmd_create() {
  if [ "$DRY" = 0 ] && existe; then echo "CT $CTID ja existe: nada a criar"; return 0; fi
  ssh_pve "pct create $CTID '$TEMPLATE' --hostname $HOSTNAME_CT --cores 4 --memory 8192 --swap 1024 --rootfs $STORAGE:40 --net0 name=eth0,bridge=vmbr0,ip=$IP/24,gw=$GW,firewall=0 --unprivileged 1 --features nesting=1 --onboot 1 --description 'Lab88: CT fixo da Forja (estudio de design/divulgacao). Doc: forja/docs/estudio/forja-ct-fixo-2026-11-12.md. Remover: pct stop $CTID && pct destroy $CTID'"
  ssh_pve "pct start $CTID"
  [ "$DRY" = 1 ] || for _ in $(seq 1 20); do in_ct 'getent hosts deb.debian.org >/dev/null' 2>/dev/null && return 0; sleep 3; done
  [ "$DRY" = 1 ] || erro "CT sem rede/DNS apos 60 s"
}

cmd_provision() {
  local script
  script=$(cat <<'INSIDE'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git xz-utils gnupg jq openssh-server sudo locales \
  python3 python3-venv python3-pip poppler-utils imagemagick qpdf tcpdump time ffmpeg rsync \
  fonts-dejavu-core fonts-liberation fonts-roboto fonts-crosextra-carlito fonts-crosextra-caladea fonts-open-sans libreoffice-impress
# Helvetica Neue (template Lions) nao e redistribuivel: o substituto metrico mais proximo e Liberation Sans (sem isso cai em DejaVu)
mkdir -p /etc/fonts/conf.d
cat > /etc/fonts/conf.d/30-forja-helvetica-neue.conf <<'FONTCONF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <alias binding="same"><family>Helvetica Neue</family><prefer><family>Liberation Sans</family></prefer></alias>
</fontconfig>
FONTCONF
fc-cache -f
if ! command -v google-chrome-stable >/dev/null; then
  curl -fsSL -o /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  apt-get install -y /tmp/chrome.deb
fi
if ! command -v node >/dev/null; then
  curl -fsSL -o /tmp/nodesource_setup.sh https://deb.nodesource.com/setup_22.x
  echo "nodesource sha256: $(sha256sum /tmp/nodesource_setup.sh | awk '{print $1}')"
  bash /tmp/nodesource_setup.sh
  apt-get install -y nodejs
fi
id forja >/dev/null 2>&1 || useradd -m -s /bin/bash forja
install -d -o forja -g forja -m 0755 /srv/forja /srv/forja/acervo /srv/forja/work
install -d -o forja -g forja -m 0700 /home/forja/.ssh
printf '%s\n' '#!/bin/sh' 'exec /usr/bin/google-chrome-stable --no-sandbox --disable-dev-shm-usage --disable-gpu "$@"' > /usr/local/bin/forja-chrome
chmod 0755 /usr/local/bin/forja-chrome
cat > /etc/profile.d/forja.sh <<'PROF'
export PATH=/srv/forja/venv/bin:$PATH
export FORJA_BRAND_SOURCES=/srv/forja/acervo
export OPEN_DESIGN_BROWSER_PATH=/usr/local/bin/forja-chrome
export OPEN_DESIGN_FFMPEG_PATH=/usr/bin/ffmpeg
PROF
printf '%s\n' 'PasswordAuthentication no' 'PermitRootLogin no' 'AllowUsers forja' 'KbdInteractiveAuthentication no' > /etc/ssh/sshd_config.d/forja.conf
systemctl enable --now ssh
sudo -u forja bash -lc '
  set -euo pipefail
  [ -d /srv/forja/repo/.git ] || git clone --branch "__BRANCH__" "__REPO__" /srv/forja/repo
  git -C /srv/forja/repo pull --ff-only
  [ -x /srv/forja/venv/bin/pip ] || python3 -m venv /srv/forja/venv
  /srv/forja/venv/bin/pip install --quiet --upgrade pip
  /srv/forja/venv/bin/pip install --quiet -e "/srv/forja/repo[test]"
'
echo "provision ok"
INSIDE
)
  script=${script//__BRANCH__/$BRANCH}
  script=${script//__REPO__/$REPO_URL}
  in_ct "$script"
}

cmd_keys() {
  # reaproveita a confianca que o PVE ja tem: so as chaves do Mac, do agente DSH e do host OCI
  if [ "$DRY" = 1 ]; then echo "[dry-run] copiar chaves mac/dsh-agent/oci do PVE para /home/forja/.ssh/authorized_keys"; return 0; fi
  ssh $SSH_OPTS "$PVE_HOST" "grep -E 'alisonglima@mac|dsh-agent@oci|ubuntu@oci-lab88' /root/.ssh/authorized_keys" \
    | ssh $SSH_OPTS "$PVE_HOST" "pct exec $CTID -- bash -c 'cat > /home/forja/.ssh/authorized_keys && chown forja:forja /home/forja/.ssh/authorized_keys && chmod 600 /home/forja/.ssh/authorized_keys && wc -l < /home/forja/.ssh/authorized_keys'"
}

ok=0; falhas=0
chk() { # chk "descricao" comando...
  local d=$1; shift
  if "$@" >/dev/null 2>&1; then echo "ok:    $d"; ok=$((ok+1)); else echo "FALHA: $d"; falhas=$((falhas+1)); fi
}

cmd_verify() {
  chk "CT $CTID em execucao" bash -c "ssh $SSH_OPTS $PVE_HOST 'pct status $CTID' | grep -q running"
  chk "onboot=1" bash -c "ssh $SSH_OPTS $PVE_HOST 'pct config $CTID' | grep -q '^onboot: 1'"
  chk "Mac -> CT (ssh forja@$IP)" ssh $SSH_OPTS $NEW forja@"$IP" "bash -lc 'forja --help'"
  chk "OCI host -> CT" ssh $SSH_OPTS oci-lab88 "ssh $SSH_OPTS $NEW forja@$IP true"
  chk "agente DSH -> CT (via proxmox)" ssh $SSH_OPTS oci-lab88 "sudo docker exec dsh ssh $SSH_OPTS $NEW -J $PVE_HOST forja@$IP true"
  chk "root por SSH recusado" bash -c "! ssh $SSH_OPTS -o PasswordAuthentication=no root@$IP true"
  echo "resumo: $ok ok, $falhas falhas"; [ "$falhas" = 0 ]
}

cmd_status() { ssh_pve "pct status $CTID; pct config $CTID | grep -E '^(hostname|cores|memory|rootfs|net0|onboot)'"; }

sub=${1:-}; shift || true
[ "${1:-}" = "--dry-run" ] && DRY=1
case "$sub" in
  create) cmd_create ;; provision) cmd_provision ;; keys) cmd_keys ;;
  verify) cmd_verify ;; status) cmd_status ;;
  *) erro "uso: $0 {create|provision|keys|verify|status} [--dry-run]" ;;
esac
