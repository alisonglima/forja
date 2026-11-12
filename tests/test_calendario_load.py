"""Contrato de `forja/calendario.py` (L-CAL-LOAD-01), do plano.

`load_calendar(path=None) -> dict` le o JSON empacotado ou um caminho explicito
e devolve `schema_version`, `ano`, `datas` (plano:2603, 2927); cada data tem
`data`, `nome`, `pilar`, `fonte`, `checked_at`, e sao 15 linhas (plano:2634).
`stale_rows(data, on=None, days=90)` avisa `checked_at` com mais de 90 dias, como
`formats` (plano:335/765), sem erro; data/pilar/fonte/checked_at sao obrigatorios.
"""
import json

import pytest

def _row(**kw):
    row = {"data": "2027-01-01", "nome": "Ano Novo", "pilar": "prestação de contas",
           "fonte": "https://example.test/ano-novo", "checked_at": "2026-11-11"}
    row.update(kw)
    return row


def _doc(*rows):
    return {"schema_version": 1, "ano": 2027, "datas": list(rows)}


def _write(tmp_path, payload):
    path = tmp_path / "calendario.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_calendar_reads_explicit_path(tmp_path):
    from forja import calendario
    data = calendario.load_calendar(_write(tmp_path, _doc(_row())))
    assert (data["schema_version"], data["ano"]) == (1, 2027)
    assert [(r["data"], r["pilar"]) for r in data["datas"]] == [("2027-01-01", "prestação de contas")]


def test_default_path_loads_the_fifteen_packaged_dates():
    from forja import calendario
    datas = calendario.load_calendar()["datas"]
    assert len(datas) == 15
    assert datas[0]["data"] == "2027-01-01"


@pytest.mark.parametrize("campo", ["data", "pilar", "fonte", "checked_at"])
def test_load_calendar_rejects_missing_required_field(tmp_path, campo):
    from forja import calendario
    row = _row()
    del row[campo]
    # LACUNA: o contrato manda garantir data/URL/pilar, mas nao nomeia a excecao.
    with pytest.raises(Exception):
        calendario.load_calendar(_write(tmp_path, _doc(row)))


def test_empty_document_has_no_dates_and_no_stale_rows(tmp_path):
    from forja import calendario
    data = calendario.load_calendar(_write(tmp_path, _doc()))
    assert data["datas"] == [] and calendario.stale_rows(data, on="2026-04-01") == []


@pytest.mark.parametrize("raw", ['{"datas": [', '[]', None])
def test_load_calendar_rejects_bad_or_missing_input(tmp_path, raw):
    from forja import calendario
    path = tmp_path / "calendario.json"
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
    with pytest.raises(Exception):
        calendario.load_calendar(path)


def test_stale_rows_uses_injected_day_and_custom_window():
    from forja import calendario
    boundary = _doc(_row(data="2026-01-01", checked_at="2026-01-01"),
                    _row(data="2026-01-02", checked_at="2025-12-31"))
    # LACUNA: o contrato nao nomeia o codigo do aviso nem a chave que carrega a data.
    issues = calendario.stale_rows(boundary, on="2026-04-01")
    assert [i["level"] for i in issues] == ["warning"] and "2026-01-02" in issues[0]["msg"]
    short = _doc(_row(data="2026-03-22", checked_at="2026-03-22"),
                 _row(data="2026-03-21", checked_at="2026-03-21"))
    issues = calendario.stale_rows(short, on="2026-04-01", days=10)
    assert len(issues) == 1 and "2026-03-21" in issues[0]["msg"]
