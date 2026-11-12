"""Contrato de `forja/formats.py` (N-11), congelado do plano.

`load_formats(path=None) -> dict` le por importlib.resources ou `path`, valida a
linha e devolve `schema_version`/`formatos` (plano:338, 726). Linha sem
`fonte`/`checked_at` e rejeitada; `fonte_tipo: oficial` exige URL http(s);
`fonte_tipo: plano` vira `provisorio` com `constantes: []` (plano:294).
`stale_rows(data, on=None, days=90)` devolve `FORMAT_STALE` `warning` com id,
dias e URL para `checked_at` com mais de 90 dias (plano:335, 765).
`get`, `require_verified` e `constantes`: nao VERIFICADO devolve
`FORMAT_UNVERIFIED` `error` (plano:336, 338).
"""
import json

import pytest

def _row(**kw):
    row = {
        "id": "ig-feed-4x5", "plataforma": "instagram", "formato": "feed-retrato",
        "largura": 1080, "altura": 1350, "razao": "4:5",
        "safe_zone": {"top": .05, "bottom": .05, "left": .05, "right": .05},
        "max_chars": 2200, "max_hashtags": 5, "alt_max": 100,
        "fonte": "https://example.test/fmt", "fonte_tipo": "oficial",
        "checked_at": "2026-11-11", "status": "confirmado",
        "verificacao": "VERIFICADO", "constantes": ["max_chars"], "notas": "",
    }
    row.update(kw)
    return row

def _doc(*rows):
    return {"schema_version": 1, "atualizado_em": "2026-11-11", "formatos": list(rows)}

def _write(tmp_path, payload):
    path = tmp_path / "formats.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path

def test_load_formats_reads_rows(tmp_path):
    from forja import formats
    data = formats.load_formats(_write(tmp_path, _doc(_row())))
    assert data["schema_version"] == 1
    assert [(r["id"], r["safe_zone"]["top"]) for r in data["formatos"]] == [("ig-feed-4x5", .05)]

# LACUNA: `stale(days=90)` sem `on` nao e testavel sem relogio real.
# LACUNA: `get(id)` inexistente nao tem comportamento definido no contrato.
def test_default_path_and_get_use_packaged_matrix():
    from forja import formats
    data = formats.load_formats()
    assert len(data["formatos"]) == 20
    assert formats.get("ig-feed-4x5")["id"] == "ig-feed-4x5"

@pytest.mark.parametrize("campo", [
    "id", "plataforma", "formato", "largura", "altura", "razao", "safe_zone",
    "max_chars", "max_hashtags", "alt_max", "fonte", "fonte_tipo", "checked_at",
    "status", "notas",
])
def test_load_formats_rejects_missing_required_field(tmp_path, campo):
    from forja import formats
    row = _row()
    del row[campo]
    # LACUNA: o contrato diz "rejeita", mas nao nomeia a excecao.
    with pytest.raises(Exception):
        formats.load_formats(_write(tmp_path, _doc(row)))

def test_load_formats_rejects_incomplete_safe_zone(tmp_path):
    from forja import formats
    with pytest.raises(Exception):
        formats.load_formats(_write(tmp_path, _doc(_row(safe_zone={"top": .05}))))

def test_load_formats_rejects_official_source_without_http_url(tmp_path):
    from forja import formats
    with pytest.raises(Exception):
        formats.load_formats(_write(tmp_path, _doc(_row(fonte="plano:5"))))

# LACUNA: o codigo do aviso de `fonte_tipo: plano` nao e nomeado; so o status e testado.
def test_plano_source_is_forced_to_provisorio_without_constants(tmp_path):
    from forja import formats
    row = _row(fonte="plano:5", fonte_tipo="plano", status="confirmado")
    got = formats.load_formats(_write(tmp_path, _doc(row)))["formatos"][0]
    assert (got["status"], got["constantes"]) == ("provisorio", [])

def test_stale_rows_flags_only_more_than_90_days():
    from forja import formats
    data = _doc(_row(id="90-dias", checked_at="2026-01-01"),
                _row(id="91-dias", checked_at="2025-12-31"))
    # LACUNA: dias/URL podem vir em `msg` ou em chaves extras; aqui exigidos em `msg`.
    issues = formats.stale_rows(data, on="2026-04-01")
    assert [(i["level"], i["id"], i["code"]) for i in issues] == [("warning", "91-dias", "FORMAT_STALE")]
    assert "91" in issues[0]["msg"] and "https://example.test/fmt" in issues[0]["msg"]

def test_stale_rows_honors_custom_days():
    from forja import formats
    data = _doc(_row(id="10", checked_at="2026-03-22"),
                _row(id="11", checked_at="2026-03-21"))
    issues = formats.stale_rows(data, on="2026-04-01", days=10)
    assert [i["id"] for i in issues] == ["11"]

def test_stale_rows_empty_document():
    from forja import formats
    assert formats.stale_rows(_doc(), on="2026-04-01") == []

# LACUNA: o contrato nao fixa se `require_verified` devolve dict ou list[dict].
def test_require_verified_and_constantes_for_divergent_row():
    from forja import formats
    assert formats.constantes("ig-feed-4x5") == []
    result = formats.require_verified("ig-feed-4x5", "max_chars")
    issues = result if isinstance(result, list) else [result]
    assert [(i["level"], i["code"]) for i in issues] == [("error", "FORMAT_UNVERIFIED")]

@pytest.mark.parametrize("raw", ['{"formatos": [', "[]"])
def test_load_formats_rejects_invalid_json_document(tmp_path, raw):
    from forja import formats
    path = tmp_path / "formats.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(Exception):
        formats.load_formats(path)

def test_load_formats_rejects_missing_file(tmp_path):
    from forja import formats
    with pytest.raises(Exception):
        formats.load_formats(tmp_path / "ausente.json")
