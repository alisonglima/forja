"""Roda os gates do Forja sobre a peça REAL (HTML composto + PNG exportado pelo kit).

Uso: python3 gates.py <dir-com-post-feed.png/post-story.png> [saida.json]
Não corrige nada: registra o que cada gate disse e onde o gate foi inadequado à entrada real.
"""
import hashlib
import json
import pathlib
import subprocess
import sys

AQUI = pathlib.Path(__file__).resolve().parent
REPO = AQUI.parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from forja import brand_lint, contrast_photo, formats, media_validate, qa_geometry, qa_visual  # noqa: E402
from forja.photo import manifest as photo_manifest  # noqa: E402

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FORMATOS = {"feed": ("ig-feed-4x5", 1350), "story": ("ig-story", 1920)}
PROBE = """<script>addEventListener('load',()=>{const q=(s)=>[...document.querySelectorAll(s)].map(e=>{const r=e.getBoundingClientRect();
return {id:e.getAttribute('data-od-field')||e.className||e.tagName,x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}});
document.title=JSON.stringify({fields:q('[data-od-field]'),emblema:q('[data-od-logo]'),foto:q('.foto'),barra:q('.barra'),
fonts:[...document.fonts].map(f=>f.family+' '+f.weight+' '+f.status)})})</script>"""


def medir_dom(html_path, esconder_texto=False):
    src = html_path.read_text(encoding="utf-8")
    extra = "<style>[data-od-field]{visibility:hidden}</style>" if esconder_texto else ""
    tmp = html_path.with_name(html_path.stem + ".probe.html")
    tmp.write_text(src.replace("</body>", PROBE + extra + "</body>"), encoding="utf-8")
    out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
                          "--virtual-time-budget=4000", "--dump-dom", f"file://{tmp}"],
                         capture_output=True, text=True, timeout=60).stdout
    tmp.unlink()
    a = out.find("<title>") + 7
    return json.loads(out[a:out.find("</title>")].replace("&quot;", '"').replace("&amp;", "&"))


def main(pasta, saida):
    pasta = pathlib.Path(pasta)
    ws = AQUI / "ws"
    variants = json.loads((REPO / "brands/leo-lions/variants.json").read_text(encoding="utf-8"))
    manifest = json.loads((REPO / "brands/leo-lions/manifest.json").read_text(encoding="utf-8"))
    tokens = dict(variants, neutrals=manifest.get("palette", manifest.get("neutrals", [])))
    fmt_data = formats.load_formats()
    res = {}
    for nome, (fid, altura) in FORMATOS.items():
        png = pasta / f"post-{nome}.png"
        html = ws / f"post-{nome}.html"
        r = res[nome] = {}
        r["brand_lint"] = brand_lint.lint_brand(html.read_text(encoding="utf-8"), tokens, "leo")
        r["measure"] = qa_geometry.measure(png)
        r["inspect_artifact"] = qa_visual.inspect_artifact(png, (1080, altura), brand_id="leo-lions")
        linha = next(x for x in (fmt_data["formatos"] if "formatos" in fmt_data else fmt_data["formats"]) if x["id"] == fid) \
            if isinstance(fmt_data, dict) and any(k in fmt_data for k in ("formatos", "formats")) else None
        r["formato_linha"] = linha
        spec = {"largura": 1080, "altura": altura, "limite_bytes": (linha or {}).get("limite_bytes")}
        r["media_validate"] = media_validate.validate_media(png, spec)
        dom = medir_dom(html)
        r["dom"] = dom
        caixas = [dict(b, id=b["id"]) for b in dom["fields"] + dom["emblema"]]
        sz = (1080, altura)
        # zona segura LIDA do formats.json (check_safe_zone, corrigido na onda L-GATEFIX-GEOM-01)
        r["safe_zone"] = {"zona": linha["safe_zone"], "issues": qa_geometry.check_safe_zone(caixas, sz, linha["safe_zone"])}
        r["overflow"] = qa_geometry.check_overflow(caixas, sz)
        # contraste: precisa de imagem de FUNDO sem texto (o gate mede todos os pixels da caixa)
        sem_texto = pasta / f"fundo-sem-texto-{nome}.png"
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--allow-file-access-from-files", "--hide-scrollbars",
                        f"--window-size=1080,{altura}", f"--screenshot={sem_texto}",
                        f"file://{_sem_texto(html)}"], capture_output=True, timeout=60)
        fundo = np.array(Image.open(sem_texto).convert("RGB"))
        r["contraste_sob_texto"] = {}
        for b in dom["fields"]:
            box = (b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"])
            r["contraste_sob_texto"][b["id"]] = contrast_photo.photo_contrast(fundo, box, "#FFFFFF", min_ratio=3.0)  # texto branco; todos os campos >= 24 px = texto grande (plano 469/563: 3:1)
        full = np.array(Image.open(png).convert("RGB"))
        b0 = dom["fields"][0]
        r["contraste_no_png_final_com_texto(uso_errado)"] = contrast_photo.photo_contrast(
            full, (b0["x"], b0["y"], b0["x"] + b0["w"], b0["y"] + b0["h"]), "#FFFFFF", min_ratio=3.0)
    # proveniência da foto
    foto_src = REPO / ".work/fontes/lions/box-extra/G-fotos-biblioteca/_Environment/2015_03_16_California_Seal Beach_Clean up_Service Project_Leos_Lions - 02.jpg"
    sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
    m = photo_manifest.build_manifest(
        input_sha256=sha(foto_src), output_sha256=sha(ws / "assets/foto-feed.jpg"),
        steps=[{"name": "crop_focal", "params": {"focal": [0.5, 0.5], "target": [2160, 1680]}}],
        brand_id="leo-lions", origin="Lions Clubs International - biblioteca de fotos (box-extra/G-fotos-biblioteca/_Environment)",
        license="(c) Lions Clubs International; uso autorizado a associados; termos da biblioteca NAO verificados", ai_elements=[])
    res["manifesto_foto"] = {"manifest": m, "verify": photo_manifest.verify_manifest(m)}
    pathlib.Path(saida).write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("gravado", saida)


def _sem_texto(html):
    out = html.with_name(html.stem + ".sem-texto.html")
    out.write_text(html.read_text(encoding="utf-8").replace("</body>", "<style>[data-od-field]{visibility:hidden}</style></body>"), encoding="utf-8")
    return out


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else str(AQUI / "gates-resultado.json"))
