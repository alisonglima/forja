#!/usr/bin/env bash
# Monta o workspace do kit: HTML compostos + sidecars + assets + fontes (dentro de .work, nunca rastreado)
set -euo pipefail
cd "$(dirname "$0")"
rm -rf ws && mkdir -p ws/.open-design ws/assets ws/fonts ws/logos/Emblemas_de_Leos
python3 compose.py feed ws/post-feed.html
python3 compose.py story ws/post-story.html
cp assets/foto-*.jpg ws/assets/ && cp fonts/* ws/fonts/
cp ../fontes/lions/logos/Emblemas_de_Leos/109141433__Logo_rgb_Leo_2C.png ws/logos/Emblemas_de_Leos/
for f in feed story; do
  fmt=ig-feed-4x5; [ "$f" = story ] && fmt=ig-story
  printf '{\n  "version": 1,\n  "kind": "html",\n  "renderer": "html",\n  "status": "complete",\n  "exports": ["png"],\n  "metadata": { "format": "%s" }\n}\n' "$fmt" > ws/post-$f.html.artifact.json
done
echo "ws ok"
