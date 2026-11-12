"""T-BRAND-VOICE-01: congela `brands/leo-lions/voice.json` (NOVO; dado, sem codigo).
Schema `forja-brand-voice/v1`; `tom`, `exemplos_titulo[3]`, `termos_proibidos[]`, `origem` guia+pagina por
variante, so o do guia (plano:1995,2080); 3 variantes lions|leo|leo-lion, exemplos leo/leo-lion do guia
(plano:62,1981-1983); voz Lions breve/ativa + "Nos Servimos" (plano:1981); sem `status` (plano:1970).
"""
import json
from pathlib import Path

import pytest

LEO = ["Leos get things done.", "Leo like you mean it.", "Where there's a need, there's a Leo."]
LL = ["A new breed of Lion.", "Lion, your way.", "There's a different way to Lion."]


def _path():
    return Path(__file__).resolve().parents[1] / "brands" / "leo-lions" / "voice.json"


def _load(p=None):
    return json.loads(Path(p or _path()).read_text(encoding="utf-8"))


# LACUNA: plano:1995 nao fixa a chave do bloco ("variantes"/"variants"/topo); aceita as 3 formas.
def _vars(d):
    cands = [d.get(k) for k in ("variantes", "variants")] if isinstance(d, dict) else []
    for b in cands:
        if isinstance(b, dict) and set(b) == {"lions", "leo", "leo-lion"}:
            return b
    if isinstance(d, dict) and all(k in d for k in ("lions", "leo", "leo-lion")):
        return {k: d[k] for k in ("lions", "leo", "leo-lion")}
    raise AssertionError("voice.json sem as 3 variantes lions|leo|leo-lion")


def _n(s):
    return str(s).replace("\u2019", "'").strip()


def _org(o):
    return " ".join(str(v) for v in o.values()) if isinstance(o, dict) else str(o)


def test_schema_e_forja_brand_voice_v1():
    assert _load()["schema"] == "forja-brand-voice/v1"


def test_tem_as_tres_variantes_exatas():
    assert set(_vars(_load())) == {"lions", "leo", "leo-lion"}


def test_tom_nao_vazio_e_distinto_por_variante():
    tons = [v["tom"].strip() for v in _vars(_load()).values()]
    assert all(isinstance(t, str) and len(t) >= 10 for t in tons)
    assert len(set(tons)) == 3


def test_exemplos_leo_sao_os_tres_do_guia():
    assert [_n(e) for e in _vars(_load())["leo"]["exemplos_titulo"]] == LEO


def test_exemplos_leo_lion_sao_os_tres_do_guia():
    assert [_n(e) for e in _vars(_load())["leo-lion"]["exemplos_titulo"]] == LL


# LACUNA: plano:1981 nao lista os 3 exemplos de `lions`; congela contagem, nao texto.
def test_cada_variante_tem_tres_exemplos_distintos():
    for _id, v in _vars(_load()).items():
        ex = v["exemplos_titulo"]
        assert isinstance(ex, list) and len(ex) == 3 and all(e.strip() for e in ex)
        assert len({_n(e).lower() for e in ex}) == 3


# LACUNA: plano:1995 nao lista `termos_proibidos`; congela forma nao vazia, nao itens.
def test_termos_proibidos_sao_listas_nao_vazias_sem_repetir():
    for _id, v in _vars(_load()).items():
        ts = v["termos_proibidos"]
        assert isinstance(ts, list) and len(ts) >= 1 and all(t.strip() for t in ts)
        assert len({t.strip().lower() for t in ts}) == len(ts)


def test_origem_cita_guia_e_pagina_sem_path_traversal():
    for _id, v in _vars(_load()).items():
        txt, baixo = _org(v["origem"]), _org(v["origem"]).lower()
        assert any(k in baixo for k in ("guia", "guideline", "tokens", "brand", "v1", "v4"))
        assert any(ch.isdigit() for ch in txt) and ".." not in txt
        assert not txt.strip().startswith("/")


def test_sem_campo_status():
    dados = _load()
    assert "status" not in dados
    assert all("status" not in v for v in _vars(dados).values())


def test_arquivo_existe_e_json_dict_nao_vazio():
    assert _path().read_text(encoding="utf-8").strip() != ""
    assert isinstance(_load(), dict)


def test_rejeita_json_truncado_e_topo_lista(tmp_path):
    trunc = tmp_path / "v.json"
    trunc.write_text("{truncado", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        _load(trunc)
    lst = tmp_path / "l.json"
    lst.write_text("[1,2]", encoding="utf-8")
    with pytest.raises(AssertionError):
        _vars(_load(lst))


def test_payload_com_dois_exemplos_em_leo_falha_na_contagem(tmp_path):
    alvo = tmp_path / "v.json"
    alvo.write_text(json.dumps({"schema": "forja-brand-voice/v1", "variantes": {
        v: {"tom": "tomo" * 5, "exemplos_titulo": ["A", "B"] if v == "leo" else ["A", "B", "C"],
            "termos_proibidos": ["t1"], "origem": "guia X p.1"}
        for v in ("lions", "leo", "leo-lion")}}), encoding="utf-8")
    assert len(_vars(_load(alvo))["leo"]["exemplos_titulo"]) != 3
