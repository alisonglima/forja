#!/usr/bin/env bash
# Fase dentro do CT (FASE_CMD): check + export PNG + export PDF + prova de fonte (pdffonts) da peca real
set -uo pipefail
WS=/srv/prova/.work/peca-leo/ws
EV=/srv/prova/evidencias/peca
KIT="npx --yes @feimacode/open-design-agent-kit@0.4.0"
mkdir -p "$EV"; cd "$WS"
export OPEN_DESIGN_BROWSER_PATH=/usr/local/bin/google-chrome-prova
npx --yes @feimacode/open-design-agent-kit@0.4.0 --help > "$EV/kit-help.txt" 2>&1 || true
rodar() { local nome=$1; shift; echo "\$ $*" >> "$EV/comandos.log"; "$@" > "$EV/$nome.out" 2> "$EV/$nome.err"; local rc=$?; echo "$rc" > "$EV/$nome.exit"; echo "$nome exit=$rc"; }
for par in feed:1350 story:1920; do
  f=${par%%:*}; h=${par##*:}
  rodar check-$f $KIT check post-$f.html --viewport card:1080x$h --json --fail-on warning --workspace "$WS" --screenshots "$EV/shots-$f"
  rodar export-$f $KIT export post-$f.html --format png --selector '[data-od-card]' --width 1080 --height $h --scale 1 --workspace "$WS"
  cp "$WS"/exports/post-$f.png "$EV/post-$f.png" 2>/dev/null || cp "$(tail -n1 "$EV/export-$f.out" | tr -d '\r')" "$EV/post-$f.png" 2>/dev/null || true
  rodar pdf-$f $KIT export post-$f.html --format pdf --width 1080 --height $h --workspace "$WS"
  p=$(find "$WS" -name "post-$f.pdf" | head -1); [ -n "$p" ] && cp "$p" "$EV/post-$f.pdf" && pdffonts "$p" > "$EV/pdffonts-$f.txt" 2>&1; [ -n "$p" ] && pdfinfo "$p" > "$EV/pdfinfo-$f.txt" 2>&1
  identify -format '%w|%h|%[colorspace]|%z|%[opaque]\n' "$EV/post-$f.png" > "$EV/identify-$f.txt" 2>&1 || true
done
find "$WS" -path '*exports*' -type f > "$EV/arquivos-exports.txt"
fc-list | grep -ci roboto > "$EV/fc-roboto-count.txt" || true
echo FASE_PECA_FIM
