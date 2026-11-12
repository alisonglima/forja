#!/usr/bin/env bash
# Monta o workspace do kit a partir de pecas.json: HTML compostos + sidecars + assets + fontes + logos (dentro de .work, nunca rastreado)
set -euo pipefail
cd "$(dirname "$0")"
python3 prep-fotos.py > /dev/null
rm -rf ws && mkdir -p ws/.open-design ws/assets ws/fonts
cp fonts/* ws/fonts/
cp pecas.json ws/pecas.json   # a fase dentro do CT le a lista de pecas daqui
python3 - <<'PY'
import json, pathlib, shutil, subprocess
pecas = json.load(open("pecas.json", encoding="utf-8"))["pecas"]
fontes = pathlib.Path("../fontes/lions")
logos = {"logos/Emblemas_de_Leos/109141433__Logo_rgb_Leo_2C.png"}  # post-foto traz a logo no proprio template
for p in pecas:
    subprocess.run(["python3", "compose.py", p["id"], f"ws/{p['id']}.html"], check=True, stdout=subprocess.DEVNULL)
    foto = p["foto"].get("src") or f"assets/{p['id']}.jpg"
    shutil.copy(foto, "ws/assets/" + pathlib.Path(foto).name)
    if "logo" in p:
        logos.add(p["logo"]["arquivo"])
    side = {"version": 1, "kind": "html", "renderer": "html", "status": "complete", "exports": ["png"], "metadata": {"format": p["preset"]}}
    pathlib.Path(f"ws/{p['id']}.html.artifact.json").write_text(json.dumps(side, indent=2) + "\n", encoding="utf-8")
for l in logos:
    dest = pathlib.Path("ws") / l
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(fontes / l, dest)
print("ws ok:", [p["id"] for p in pecas])
PY
