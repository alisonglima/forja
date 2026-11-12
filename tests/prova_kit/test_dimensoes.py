"""Contrato da prova (a): cartao 1080x1350 e story 1080x1920 exatos (plano:2215-2235).

A evidencia p5-01-dimensoes/ tem dimensoes.json/txt, PNGs, comandos.log e sha256sums.txt; o JSON traz w, h, colorspace, bits, opaque, dpr (w/1080) e assinatura (plano:2353).
O script so executa e grava; validar() decide; amostras contrato sao sinteticas (sem rede, LXC, ffmpeg, poppler ou Chrome).
# LACUNA: topo do JSON e formato de comandos.log nao fixados; adota-se lista de registros com
#   arquivo, fonte, via, scale e sha256; comandos.log so precisa ser nao vazio.
# DIVERGENCIA: plano:2215-2235 grafa p5-01; plano:2353 grafa p5-01-dimensoes; vale K.3.
"""
from __future__ import annotations
import json, os, re
from pathlib import Path
import pytest

ARQUIVOS = ("dimensoes.json", "dimensoes.txt", "comandos.log", "sha256sums.txt")
BASE = {"cartao": (1080, 1350), "story": (1080, 1920)}
VIAS = ("selector", "preset", "width-height", "scale2")
CAMPOS = ("arquivo", "fonte", "via", "scale", "w", "h", "colorspace", "bits",
          "opaque", "dpr", "assinatura", "sha256")

def _normalizar(ev):
    if isinstance(ev, dict):
        return dict(ev)
    d = Path(ev)
    if not d.is_dir():
        return {"faltando": [f"evidencia ausente: {d}"]}
    dados = {"pngs": sorted(p.name for p in d.glob("*.png"))}
    for nome in ARQUIVOS:
        p = d / nome
        dados[nome] = p.read_text(encoding="utf-8") if p.is_file() else None
    return dados

def validar(ev):
    """Lista de problemas da evidencia; [] = contrato cumprido."""
    ev = _normalizar(ev)
    p = list(ev.get("faltando", []))
    if p: return p
    p += [f"arquivo ausente ou vazio: {n}" for n in ARQUIVOS if not ev.get(n)]
    doc = ev.get("dimensoes.json")
    if isinstance(doc, str):
        try:
            doc = json.loads(doc)
        except ValueError as exc:
            return p + [f"dimensoes.json invalido: {exc}"]
    if not isinstance(doc, list) or not doc:
        return p + ["dimensoes.json: lista vazia ou invalida"]
    pngs, txt = set(ev.get("pngs") or []), ev.get("dimensoes.txt") or ""
    for i, r in enumerate(doc):
        if not isinstance(r, dict):
            p.append(f"runs[{i}]: nao e objeto")
            continue
        p += [f"runs[{i}]: campo ausente {c}" for c in CAMPOS if c not in r]
        arq, fonte, via, scale = (r.get(k) for k in ("arquivo", "fonte", "via", "scale"))
        base = BASE.get(fonte) if isinstance(fonte, str) else None
        if not isinstance(arq, str) or arq not in pngs:
            p.append(f"runs[{i}]: PNG ausente {arq!r}")
        if not base or scale not in (1, 2):
            p.append(f"runs[{i}]: fonte/scale invalidos")
        elif (r.get("w"), r.get("h")) != (base[0] * scale, base[1] * scale):
            p.append(f"runs[{i}]: dimensao fora do criterio")
        if not isinstance(via, str) or via not in VIAS:
            p.append(f"runs[{i}]: via invalida {via!r}")
        if (r.get("colorspace"), r.get("bits"), r.get("opaque")) != ("sRGB", 8, True):
            p.append(f"runs[{i}]: PNG nao e 8 bits sRGB opaco")
        if r.get("dpr") != scale:
            p.append(f"runs[{i}]: dpr != scale")
        if not r.get("assinatura") or not re.fullmatch(r"[0-9a-f]{64}", r.get("sha256") or ""):
            p.append(f"runs[{i}]: assinatura/sha256 ausente")
        if isinstance(arq, str) and f"{arq} {r.get('w')}x{r.get('h')}" not in txt:
            p.append(f"runs[{i}]: dimensoes.txt sem {arq}")
    variantes = {(r.get("fonte"), r.get("via")) for r in doc if isinstance(r, dict)}
    for fonte, via in (("cartao", "selector"), ("cartao", "preset"), ("cartao", "width-height"), ("story", "preset"), ("cartao", "scale2")):
        if (fonte, via) not in variantes:
            p.append(f"variante ausente: {fonte}/{via}")
    grupos = {}
    for r in doc:
        if isinstance(r, dict): grupos.setdefault((r.get("fonte"), r.get("via"), r.get("scale")), set()).add(r.get("assinatura"))
    p += [f"assinaturas divergem em {k}" for k, v in grupos.items() if len(v) > 1]
    a, b = grupos.get(("cartao", "preset", 1)), grupos.get(("cartao", "width-height", 1))
    if a and b and a != b:
        p.append("preset e width/height divergem")
    return p

def _run(arq, fonte, via, scale=1, sig="a", sha="1"):
    w, h = BASE[fonte]
    return {"arquivo": arq, "fonte": fonte, "via": via, "scale": scale, "w": w * scale,
            "h": h * scale, "colorspace": "sRGB", "bits": 8, "opaque": True,
            "dpr": float(scale), "assinatura": sig * 64, "sha256": sha * 64}

def _ev():
    runs = [_run("cartao-selector-1.png", "cartao", "selector"),
            _run("cartao-selector-2.png", "cartao", "selector"),
            _run("cartao-preset.png", "cartao", "preset", sha="2"),
            _run("cartao-wh.png", "cartao", "width-height", sha="3"),
            _run("story-preset.png", "story", "preset", sig="b", sha="4"),
            _run("cartao-scale2.png", "cartao", "scale2", scale=2, sig="c", sha="5")]
    return {"dimensoes.json": runs,
            "dimensoes.txt": "\n".join(f"{r['arquivo']} {r['w']}x{r['h']} {r['assinatura']}" for r in runs),
            "sha256sums.txt": "\n".join(f"{r['sha256']}  {r['arquivo']}" for r in runs),
            "comandos.log": "--selector\n--preset\n--width\n--height\n--scale\n",
            "pngs": [r["arquivo"] for r in runs]}

def test_contrato_amostra_valida(tmp_path):
    assert validar(_ev()) == []
    ev = _ev()
    (tmp_path / "dimensoes.json").write_text(json.dumps(ev["dimensoes.json"]), encoding="utf-8")
    for nome in ("dimensoes.txt", "sha256sums.txt", "comandos.log"):
        (tmp_path / nome).write_text(ev[nome], encoding="utf-8")
    for png in ev["pngs"]:
        (tmp_path / png).write_bytes(b"\x89PNG")
    assert validar(tmp_path) == []

def test_contrato_arquivo_ausente():
    ev = _ev(); del ev["comandos.log"]
    assert any("comandos.log" in x and "ausente" in x for x in validar(ev))

def test_contrato_valor_fora_do_criterio():
    ev = _ev(); ev["dimensoes.json"][0]["w"] = 1081
    assert any("fora do criterio" in x for x in validar(ev))
    ev = _ev(); ev["dimensoes.json"][2]["colorspace"] = "AdobeRGB"
    assert any("sRGB" in x for x in validar(ev))

def test_contrato_json_truncado_ou_vazio(tmp_path):
    for texto in ("{truncado", ""):
        (tmp_path / "dimensoes.json").write_text(texto, encoding="utf-8")
        assert any("invalido" in x for x in validar(tmp_path))

def test_contrato_hash_e_assinatura():
    ev = _ev(); ev["dimensoes.json"][0]["sha256"] = ""
    assert any("sha256" in x for x in validar(ev))
    ev = _ev(); ev["dimensoes.json"][2]["assinatura"] = "z" * 64
    assert any("divergem" in x for x in validar(ev))
    ev = _ev(); ev["dimensoes.json"][-1]["dpr"] = 1.0
    assert any("dpr" in x for x in validar(ev))

def test_evidencia_real():
    if os.environ.get("FORJA_PROVA_KIT") != "1":
        pytest.skip("defina FORJA_PROVA_KIT=1 depois da lane de prova")
    raiz = Path(__file__).resolve().parents[2]
    problemas = validar(raiz / ".work" / "prova-kit" / "evidencias" / "p5-01-dimensoes")
    assert not problemas, problemas
