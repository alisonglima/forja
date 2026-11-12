"""Roda os gates do Forja sobre cada peca de pecas.json (HTML composto + PNG).

Uso: python3 gates.py <dir-com-<id>.png> [saida.json] [id ...]
     python3 gates.py --mac [saida.json] [id ...]      (usa shots/<id>.png do Chrome do Mac: so para calibrar o design)
Nao corrige nada: registra o que cada gate disse. O texto-fonte e checado contra grafia.json (nunca o render).
"""
import hashlib
import json
import pathlib
import subprocess
import sys

AQUI = pathlib.Path(__file__).resolve().parent
REPO = AQUI.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(AQUI))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import compose  # noqa: E402
from forja import brand_lint, contrast_photo, formats, media_validate, qa_geometry, qa_visual  # noqa: E402
from forja.photo import manifest as photo_manifest  # noqa: E402

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROBE = """<script>addEventListener('load',()=>{const hex=(c)=>'#'+c.match(/\\d+/g).slice(0,3).map(n=>(+n).toString(16).padStart(2,'0')).join('');
const q=(s)=>[...document.querySelectorAll(s)].map(e=>{const rg=document.createRange();rg.selectNodeContents(e);const r=e.hasAttribute('data-od-logo')?e.getBoundingClientRect():rg.getBoundingClientRect();
return {id:e.getAttribute('data-od-field')||e.className||e.tagName,x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height),cor:hex(getComputedStyle(e).color),px:parseFloat(getComputedStyle(e).fontSize)}});
document.title=JSON.stringify({fields:q('[data-od-field]'),emblema:q('[data-od-logo]'),fonts:[...document.fonts].map(f=>f.family+' '+f.weight+' '+f.status)})})</script>"""


def _chrome(args, html_path):
    return subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--allow-file-access-from-files", "--hide-scrollbars", *args,
                           f"file://{html_path}"], capture_output=True, text=True, timeout=90)


def medir_dom(html_path):
    tmp = html_path.with_name(html_path.stem + ".probe.html")
    tmp.write_text(html_path.read_text(encoding="utf-8").replace("</body>", PROBE + "</body>"), encoding="utf-8")
    out = _chrome(["--virtual-time-budget=4000", "--dump-dom"], tmp).stdout
    tmp.unlink()
    a = out.find("<title>") + 7
    return json.loads(out[a:out.find("</title>")].replace("&quot;", '"').replace("&amp;", "&"))


def sem_texto(html_path, altura, destino):
    """Render do FUNDO sem o texto (color:transparent mantem a caixa branca do rotulo), para medir contraste real."""
    tmp = html_path.with_name(html_path.stem + ".sem-texto.html")
    tmp.write_text(html_path.read_text(encoding="utf-8").replace(
        "</body>", "<style>[data-od-field]{color:transparent !important}</style></body>"), encoding="utf-8")
    _chrome([f"--window-size=1080,{altura}", "--virtual-time-budget=4000", f"--screenshot={destino}"], tmp)
    tmp.unlink()
    return np.array(Image.open(destino).convert("RGB"))


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def gates_peca(p, png, ws, tokens, fmt_data):
    r = {}
    html = ws / f"{p['id']}.html"
    copy = json.loads((AQUI / p["copy_arquivo"]).read_text(encoding="utf-8")) if "copy_arquivo" in p else p["copy"]
    r["grafia_texto_fonte"] = compose.grafia_erros(copy, p["idioma"])
    r["brand_lint"] = brand_lint.lint_brand(html.read_text(encoding="utf-8"), tokens, p["marca"], logos=p.get("logos_extra"), rules=p.get("regras"))
    r["measure"] = qa_geometry.measure(png)
    r["inspect_artifact"] = qa_visual.inspect_artifact(png, (1080, p["altura"]), brand_id="leo-lions")
    linha = next(x for x in fmt_data["formatos"] if x["id"] == p["preset"])
    r["media_validate"] = media_validate.validate_media(png, {"largura": 1080, "altura": p["altura"], "limite_bytes": linha.get("limite_bytes")})
    dom = r["dom"] = medir_dom(html)
    caixas = dom["fields"] + dom["emblema"]
    sz = (1080, p["altura"])
    r["safe_zone"] = {"zona": linha["safe_zone"], "issues": qa_geometry.check_safe_zone(caixas, sz, linha["safe_zone"])}
    r["overflow"] = qa_geometry.check_overflow(caixas, sz)
    fundo = sem_texto(html, p["altura"], png.with_name(f"{p['id']}.fundo-sem-texto.png"))
    r["contraste_sob_texto"] = {}
    for b in dom["fields"]:
        grande = b["px"] >= 24
        r["contraste_sob_texto"][b["id"]] = contrast_photo.photo_contrast(
            fundo, (b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]), b["cor"], min_ratio=3.0 if grande else 4.5)
    r["texto_pequeno(<24px)"] = [b["id"] for b in dom["fields"] if b["px"] < 24]
    if "origem" in p["foto"]:
        origem = REPO / ".work/fontes/lions" / p["foto"]["origem"]
        m = photo_manifest.build_manifest(
            input_sha256=sha(origem), output_sha256=sha(AQUI / "assets" / f"{p['id']}.jpg"),
            steps=[{"name": "crop_focal", "params": {"focal": p["foto"]["focal"], "target": [1080, p["altura"]]}}],
            brand_id="leo-lions", origin="Lions Clubs International - biblioteca de fotos (" + p["foto"]["origem"].rsplit("/", 1)[0] + ")",
            license="(c) Lions Clubs International; uso autorizado a associados; termos da biblioteca NAO verificados", ai_elements=[])
        r["manifesto_foto"] = {"verify": photo_manifest.verify_manifest(m)}
    return r


def main(argv):
    mac = "--mac" in argv
    args = [a for a in argv if a != "--mac"]
    pasta = None if mac else pathlib.Path(args.pop(0))
    saida = next((a for a in args if a.endswith(".json")), str(AQUI / "gates-resultado.json"))
    ids = [a for a in args if not a.endswith(".json")]
    ws = AQUI / "ws"
    variants = json.loads((REPO / "brands/leo-lions/variants.json").read_text(encoding="utf-8"))
    manifest = json.loads((REPO / "brands/leo-lions/manifest.json").read_text(encoding="utf-8"))
    tokens = dict(variants, neutrals=manifest.get("palette", manifest.get("neutrals", [])))
    fmt_data = formats.load_formats()
    res = {}
    for p in json.loads((AQUI / "pecas.json").read_text(encoding="utf-8"))["pecas"]:
        if ids and p["id"] not in ids:
            continue
        png = (AQUI / "shots" / f"{p['id']}.png") if mac else pasta / f"{p['id']}.png"
        res[p["id"]] = gates_peca(p, png, ws, tokens, fmt_data)
    pathlib.Path(saida).write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    for i, r in res.items():
        c = {k: round(v["min"], 2) for k, v in r["contraste_sob_texto"].items()}
        print(f"{i}: grafia={r['grafia_texto_fonte']} lint={len(r['brand_lint'])} zona={len(r['safe_zone']['issues'])} "
              f"overflow={len(r['overflow'])} media={len(r['media_validate'])} contraste_min={c}")


if __name__ == "__main__":
    main(sys.argv[1:])
