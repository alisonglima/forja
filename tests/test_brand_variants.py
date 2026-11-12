"""Contrato de `brands/leo-lions/variants.json` (dado versionado; sem código).
Congela `L-BRAND-VARIANTS-01`: schema `forja-brand-variants/v1` e 3 variantes
exatas `lions`/`leo`/`leo-lion` (plano:62, plano:2079); paletas, papéis e
`--accent` único (`lions`/`leo-lion` `#00338D`, `leo` `#00AB68` sem o azul 287;
plano:1979-1983, plano:2032-2035); emblema permitido/proibido, elemento,
Roboto, tom, exemplos e fundo (plano:1981-1983); `fonte` arquivo+página por
variante, sem `status` (plano:1970, plano:1994) e sem binário. O JSON é lido
em tempo de teste: `--collect-only` passa sem a implementação.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "brands" / "leo-lions" / "variants.json"

SCHEMA = "forja-brand-variants/v1"
IDS = ["lions", "leo", "leo-lion"]
ACCENTS = {"lions": "#00338d", "leo": "#00ab68", "leo-lion": "#00338d"}
PRIM = {"lions": {"#00338d", "#ebb700", "#7a2582"},
        "leo": {"#55565a", "#ebb700", "#407cca", "#00ab68"},
        "leo-lion": {"#00338d", "#55565a", "#407cca", "#ebb700"}}
LEO_EX = ["Leos get things done.", "Leo like you mean it.", "Where there's a need, there's a Leo."]
LEO_LION_EX = ["A new breed of Lion.", "Lion, your way.", "There's a different way to Lion."]
FONTES = {"lions": "tokens-oficiais.json", "leo": "tokens-submarcas.json", "leo-lion": "tokens-submarcas.json"}
CHAVES = ("accent", "paleta", "emblema", "elemento", "tipografia", "tom", "fundo", "fonte")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
PAG = re.compile(r"p\.?\s*\d|p[aá]gina", re.IGNORECASE)

def _load(path=PATH):
    assert path.exists(), "variants.json ausente: %s" % path
    return json.loads(path.read_text(encoding="utf-8"))

def _texto(fonte):
    return " ".join(str(x) for x in fonte.values()) if isinstance(fonte, dict) else str(fonte)

def _fonte_ok(fonte, oficial):
    t, k = _texto(fonte), " ".join(fonte).lower() if isinstance(fonte, dict) else ""
    return oficial in t and ("pag" in k or bool(PAG.search(t))) and ".." not in t and not t.strip().startswith("/")

def _hexes(v):
    return [h.lower() for h in v.get("paleta", {}).values() if isinstance(h, str)]

def _issues(doc):
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        return ["schema"]
    vs = doc.get("variants")
    if not isinstance(vs, dict) or sorted(vs) != sorted(IDS):
        return ["variants"]
    out = []
    for vid in IDS:
        v = vs[vid]
        if not isinstance(v, dict):
            return ["tipo:%s" % vid]
        out += ["chave:%s:%s" % (vid, c) for c in CHAVES if not v.get(c)]
        if "status" in v:
            out.append("status")
        if not (isinstance(v.get("accent"), str) and v["accent"].lower() == ACCENTS[vid]):
            out.append("accent:%s" % vid)
        if any(not HEX.match(h) for h in _hexes(v)):
            out.append("hex:%s" % vid)
        if vid == "leo" and "#00338d" in _hexes(v):
            out.append("leo-287")
        if not _fonte_ok(v.get("fonte"), FONTES[vid]):
            out.append("fonte:%s" % vid)
    return out + (["status"] if "status" in doc else [])

def test_arquivo_schema_e_variantes():
    doc = _load()
    assert doc["schema"] == SCHEMA and sorted(doc["variants"]) == sorted(IDS)

def test_accents_unicos_e_oficiais():
    doc = _load()
    assert {v: doc["variants"][v]["accent"].lower() for v in IDS} == ACCENTS
    assert "accent-2" not in PATH.read_text(encoding="utf-8")

def test_paletas_primarias_e_hex():
    doc = _load()
    for vid in IDS:
        assert PRIM[vid] <= set(_hexes(doc["variants"][vid]))
        assert all(HEX.match(h) for h in doc["variants"][vid]["paleta"].values())

def test_leo_sem_azul_287():
    leo = _load()["variants"]["leo"]
    assert "#00338d" not in _hexes(leo) and "287" in str(leo["fundo"])

def test_emblemas_permitidos_e_proibidos():
    emb = {v: _load()["variants"][v]["emblema"] for v in IDS}
    assert "Emblemas_do_Lions" in str(emb["lions"]["permitido"])
    assert "Emblemas_de_Leos" in str(emb["leo"]["permitido"])
    assert "Logotipos_de_Leo_a_Leão" in str(emb["leo-lion"]["permitido"])
    assert "recolorir" in str(emb["lions"]["proibido"]).lower()
    assert "Lions" in str(emb["leo"]["proibido"]) and "Alpha" in str(emb["leo"]["proibido"])
    assert "fundo azul" in str(emb["leo-lion"]["proibido"]).lower()

def test_elemento_tipografia_fundo():
    doc = _load()
    assert "seta" in str(doc["variants"]["leo"]["elemento"]).lower()
    assert "fita" in str(doc["variants"]["leo-lion"]["elemento"]).lower()
    for vid in IDS:
        assert "Roboto" in str(doc["variants"][vid]["tipografia"])
        assert str(doc["variants"][vid]["fundo"]).strip() != ""

def test_exemplos_do_guia():
    doc = _load()
    assert doc["variants"]["leo"]["exemplos"] == LEO_EX
    assert doc["variants"]["leo-lion"]["exemplos"] == LEO_LION_EX
    # LACUNA: plano não lista exemplos de `lions` (plano:1981); nada se afirma sobre eles.

def test_fonte_arquivo_e_pagina():
    doc = _load()
    for vid in IDS:
        assert _fonte_ok(doc["variants"][vid]["fonte"], FONTES[vid]) is True

def test_sem_status_nem_binario():
    doc = _load()
    assert "status" not in doc and all("status" not in doc["variants"][v] for v in IDS)
    texto = PATH.read_text(encoding="utf-8")
    assert "data:image/" not in texto and "data:application/" not in texto
    assert '"base64"' not in texto.lower() and '"blob"' not in texto.lower()

def test_doc_vazio_ou_sem_variantes_falha():
    assert _issues({}) == ["schema"]
    assert _issues({"schema": SCHEMA, "variants": {}}) == ["variants"]

def test_json_truncado_falha(tmp_path):
    alvo = tmp_path / "variants.json"
    alvo.write_text('{"schema": "forja-brand-variants/v1",', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        json.loads(alvo.read_text(encoding="utf-8"))

def test_tipo_errado_falha():
    assert _issues({"schema": SCHEMA, "variants": ["lions"]}) == ["variants"]
    doc = {"schema": SCHEMA, "variants": {"lions": {}, "leo": {"accent": ["#00AB68"]}, "leo-lion": {}}}
    assert "accent:leo" in _issues(doc)

def test_fonte_com_dotdot_falha():
    leo = {"accent": "#00AB68", "paleta": {"c": "#55565A"}, "emblema": {"p": "x"}, "elemento": "s", "tipografia": "R", "tom": "t", "fundo": "f", "fonte": "../tokens-submarcas.json p.4"}
    assert "fonte:leo" in _issues({"schema": SCHEMA, "variants": {"lions": {}, "leo": leo, "leo-lion": {}}})
