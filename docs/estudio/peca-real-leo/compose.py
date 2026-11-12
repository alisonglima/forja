"""Compose interino das pecas Instagram: template neutro + tokens da marca + copy -> HTML final.

Uso: python3 compose.py <id-da-peca> <saida.html>      (as pecas vivem em pecas.json)
- `/*TOKENS*/` vira :root{--...} so com os tokens que o template usa (cores de brands/leo-lions/variants.json).
- `{{campo}}` recebe o valor com escape HTML; `<!--opt:x-->...<!--/opt:x-->` some se o campo x for vazio.
- Falha se: hex cru no template, placeholder sem valor, ou texto pt-BR com "Leo"/"Leos" (grafia: brands/leo-lions/grafia.json).
- A logo e medida pela area VISIVEL (alfa): a caixa recorta a margem transparente, entao caixa medida = desenho.
"""
import html
import json
import pathlib
import re
import sys

from PIL import Image

AQUI = pathlib.Path(__file__).resolve().parent
REPO = AQUI.parents[1]
FONTES = REPO / ".work/fontes/lions"
BRANDS = REPO / "brands/leo-lions"


def grafia_erros(copy, idioma):
    """Texto-fonte (nunca o render): em pt-BR a sigla e LEO/LEOs."""
    if idioma != "pt-BR":
        return []
    cfg = json.loads((BRANDS / "grafia.json").read_text(encoding="utf-8"))
    regras = [(re.compile(r["padrao"]), r["mensagem"]) for r in cfg["verificacao"]["reprova"]]
    return [f"{campo}: '{m.group(0)}' ({msg})"
            for campo, valor in copy.items() if isinstance(valor, str)
            for rx, msg in regras for m in rx.finditer(valor.replace("\u2019", "'"))]


def geometria_logo(arquivo, largura_visivel):
    """Caixa = area visivel da logo (alfa); devolve px da imagem inteira, da caixa e das margens negativas."""
    im = Image.open(FONTES / arquivo).convert("RGBA")
    x0, y0, x1, y1 = im.split()[3].point(lambda v: 255 if v > 8 else 0).getbbox()
    W, H = im.size
    escala = largura_visivel / (x1 - x0)
    return {"logo_img_w": round(W * escala), "logo_box_w": round((x1 - x0) * escala), "logo_box_h": round((y1 - y0) * escala),
            "logo_ml": -round(x0 * escala), "logo_mt": -round(y0 * escala)}


def carregar(id_):
    pecas = json.loads((AQUI / "pecas.json").read_text(encoding="utf-8"))["pecas"]
    return next(p for p in pecas if p["id"] == id_)


def main(id_, saida):
    p = carregar(id_)
    tpl = (AQUI / "template" / f"{p['template']}.html").read_text(encoding="utf-8")
    if re.search(r"#[0-9a-fA-F]{3,8}\b", tpl):
        raise SystemExit("template com hex cru")
    copy = json.loads((AQUI / p["copy_arquivo"]).read_text(encoding="utf-8")) if "copy_arquivo" in p else dict(p["copy"])
    erros = grafia_erros(copy, p["idioma"])
    if erros:
        raise SystemExit("grafia (regra do dono, 12/11/2026): " + "; ".join(erros))
    variants = json.loads((BRANDS / "variants.json").read_text(encoding="utf-8"))["variants"]
    pal = variants[p["marca"]]["paleta"]
    todos = {"white": "#FFFFFF", "yellow": pal["amarelo"], "gray": pal.get("cinza"), "sky": pal.get("azul_claro"), "green": pal.get("verde")}
    ov = p.get("overlay")
    if ov:
        todos["ov1"], todos["ov2"] = pal[ov["cor1"]], pal[ov["cor2"]]
        todos["lab"] = pal[ov.get("cor_rotulo", ov["cor1"])]  # texto do rotulo sobre caixa branca
        if ov.get("base_cor"):
            todos["base"] = pal[ov["base_cor"]]  # camada escura sob o overlay (ajuda o contraste do texto)
    usados = sorted(set(re.findall(r"var\(--([\w-]+)\)", tpl)) & {k for k, v in todos.items() if v})
    linhas = [f"  --{k}: {todos[k]};" for k in usados]
    if ov:
        linhas.append(f"  --ov-a: {ov['opacidade']};")
        linhas.append(f"  --base-a: {ov.get('base_opacidade', 0)};")
    fmt = next(f for f in json.loads((REPO / "forja/data/formats.json").read_text(encoding="utf-8"))["formatos"] if f["id"] == p["preset"])
    zona = fmt["safe_zone"]
    linhas += [f"  --h: {p['altura']}px;",
               f"  --mx: {max(72, round(zona['left'] * 1080))}px;",
               f"  --mt: {max(72, round(zona['top'] * p['altura']))}px;",
               f"  --mb: {max(72, round(zona['bottom'] * p['altura']))}px;"]
    tokens = ":root {\n" + "\n".join(linhas) + "\n}"
    foto = p["foto"].get("src") or f"assets/{p['id']}.jpg"
    campos = dict(copy, formato=p["formato"], foto=foto, emb_w=p.get("emb_w", 0), marca=p["marca"], lang=p["idioma"])
    if "logo" in p:
        campos.update(geometria_logo(p["logo"]["arquivo"], p["logo"]["largura_visivel"]), logo_src=p["logo"]["arquivo"])
    # titulo da data comemorativa: corpo auto-ajustado a largura da coluna (palavra unica, caixa alta, Roboto 900 ~0,66 em/letra)
    if "titulo" in copy:
        campos["titulo_px"] = p.get("titulo_px") or max(120, min(230, int(900 / (0.66 * max(len(copy["titulo"]), 1)))))
    if "numero" in copy:  # numero em destaque: uma linha, Roboto 900 ~0,62 em/digito
        campos["numero_px"] = max(160, min(420, int(930 / (0.62 * max(len(copy["numero"]), 1)))))
    out = tpl.replace("/*TOKENS*/", tokens)
    out = re.sub(r"<!--opt:(\w+)-->(.*?)<!--/opt:\1-->",
                 lambda m: m.group(2) if str(campos.get(m.group(1), "")).strip() else "", out, flags=re.S)
    for k, v in campos.items():
        out = out.replace("{{" + k + "}}", html.escape(str(v), quote=True))
    sobra = re.findall(r"\{\{\w+\}\}", out)
    if sobra:
        raise SystemExit(f"placeholders sem valor: {sobra}")
    pathlib.Path(saida).write_text(out, encoding="utf-8")
    print("ok", saida)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
