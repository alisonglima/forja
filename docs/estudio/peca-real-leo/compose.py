"""Compose interino da peça Leo: template neutro + tokens da variante + copy -> HTML final.

Uso: python3 compose.py <feed|story> <saida.html>
Substitui `/*TOKENS*/` por :root{--...} vindo de brands/leo-lions/variants.json (variante leo)
e preenche {{campo}} com escape HTML. Falha se sobrar {{...}} ou se o template tiver hex cru.
"""
import html
import json
import pathlib
import re
import sys

AQUI = pathlib.Path(__file__).resolve().parent
REPO = AQUI.parents[1]
FOTO = {"feed": "assets/foto-feed.jpg", "story": "assets/foto-story.jpg"}
EMB_W = {"feed": 177, "story": 240}  # largura do PNG oficial inteiro; desenho visivel = 0,699 x isto


def main(formato, saida):
    tpl = (AQUI / "template/post-foto.html").read_text(encoding="utf-8")
    if re.search(r"#[0-9a-fA-F]{3,8}\b", tpl):
        raise SystemExit("template com hex cru")
    pal = json.loads((REPO / "brands/leo-lions/variants.json").read_text(encoding="utf-8"))["variants"]["leo"]["paleta"]
    copy = json.loads((AQUI / "copy.json").read_text(encoding="utf-8"))
    todos = {"white": "#FFFFFF", "gray": pal["cinza"], "yellow": pal["amarelo"],
             "sky": pal["azul_claro"], "green": pal["verde"]}
    usados = sorted(set(re.findall(r"var\(--(\w+)\)", tpl)) & set(todos))  # so os tokens que o template usa
    tokens = ":root {\n" + "\n".join(f"  --{k}: {todos[k]};" for k in usados) + "\n}"
    campos = dict(copy, formato=formato, foto=FOTO[formato], emb_w=EMB_W[formato])
    out = tpl.replace("/*TOKENS*/", tokens)
    for k, v in campos.items():
        out = out.replace("{{" + k + "}}", html.escape(str(v), quote=True))
    sobra = re.findall(r"\{\{\w+\}\}", out)
    if sobra:
        raise SystemExit(f"placeholders sem valor: {sobra}")
    pathlib.Path(saida).write_text(out, encoding="utf-8")
    print("ok", saida)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
