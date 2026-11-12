#!/usr/bin/env bash
# Fase dentro do CT (FASE_CMD): check + export PNG + export PDF + prova de fonte (pdffonts) de TODAS as pecas de pecas.json
set -uo pipefail
WS=/srv/prova/.work/peca-leo/ws
EV=/srv/prova/evidencias/pecas
KIT="npx --yes @feimacode/open-design-agent-kit@0.4.0"
mkdir -p "$EV"; cd "$WS"
[ -s "$WS/pecas.json" ] || { echo "FASE_PECA_ERRO: $WS/pecas.json ausente"; exit 3; }
export OPEN_DESIGN_BROWSER_PATH=/usr/local/bin/google-chrome-prova
npx --yes @feimacode/open-design-agent-kit@0.4.0 --help > "$EV/kit-help.txt" 2>&1 || true
rodar() { local nome=$1; shift; echo "\$ $*" >> "$EV/comandos.log"; "$@" > "$EV/$nome.out" 2> "$EV/$nome.err"; local rc=$?; echo "$rc" > "$EV/$nome.exit"; echo "$nome exit=$rc"; }
for par in $(python3 -c "import json;print(' '.join(p['id']+':'+str(p['altura']) for p in json.load(open('/srv/prova/.work/peca-leo/ws/pecas.json'))['pecas']))"); do
  f=${par%%:*}; h=${par##*:}
  rodar check-$f $KIT check $f.html --viewport card:1080x$h --json --fail-on warning --workspace "$WS" --screenshots "$EV/shots-$f"
  rodar export-$f $KIT export $f.html --format png --selector '[data-od-card]' --width 1080 --height $h --scale 1 --workspace "$WS"
  cp "$WS"/exports/$f.png "$EV/$f.png" 2>/dev/null || cp "$(tail -n1 "$EV/export-$f.out" | tr -d '\r')" "$EV/$f.png" 2>/dev/null || true
  rodar pdf-$f $KIT export $f.html --format pdf --width 1080 --height $h --workspace "$WS"
  p=$(find "$WS" -name "$f.pdf" | head -1); [ -n "$p" ] && cp "$p" "$EV/$f.pdf" && pdffonts "$p" > "$EV/pdffonts-$f.txt" 2>&1; [ -n "$p" ] && pdfinfo "$p" > "$EV/pdfinfo-$f.txt" 2>&1
  identify -format '%w|%h|%[colorspace]|%z|%[opaque]\n' "$EV/$f.png" > "$EV/identify-$f.txt" 2>&1 || true
done
find "$WS" -path '*exports*' -type f > "$EV/arquivos-exports.txt"
fc-list | grep -ci roboto > "$EV/fc-roboto-count.txt" || true
echo FASE_PECA_FIM
