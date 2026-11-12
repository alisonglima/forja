"""Recorta as fotos do acervo para o tamanho exato da peca (crop_focal do forja). Uso: python3 prep-fotos.py"""
import json, pathlib, sys
AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1]))
from PIL import Image  # noqa: E402
from forja.photo.crop import crop_focal  # noqa: E402

FONTES = AQUI.parent / "fontes/lions"
for p in json.loads((AQUI / "pecas.json").read_text(encoding="utf-8"))["pecas"]:
    f = p["foto"]
    if "origem" not in f:
        continue
    img = Image.open(FONTES / f["origem"]).convert("RGB")
    out = crop_focal(img, f["focal"], (1080, p["altura"]))
    dest = AQUI / "assets" / f"{p['id']}.jpg"
    out.save(dest, quality=90)
    print("ok", dest.name, img.size)
