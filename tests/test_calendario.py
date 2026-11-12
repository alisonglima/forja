"""Contrato T-CAL-01 do calendario 2027 (plano:2634 cobre plano:2602).
Congela L-CAL-01: forja/data/calendario-2027.json com as 15 datas da
tabela do plano:634-658, cada linha com data/url/fonte/pilar (plano:2927
item 5), checked_at para stale_rows de 90 dias (plano:765) e "nao
encontrei" nas 2 linhas NAO VERIFICADAS 07/06 e 10/10 (plano:168). Este
arquivo so le o JSON; loader/stale_rows vivem em forja/calendario.py e
sao contrato de T-CAL-LOAD-01, outra lane.
# LACUNA: o plano nao fixa os nomes das chaves do JSON; congelo o minimo
# data/pilar/fonte/url/checked_at/verificada e aceito chaves extras.
"""
import json
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "forja" / "data" / "calendario-2027.json"
EXPECTED = ["01/01", "01-05/06", "05/06", "07/06", "14/06", "28/08", "05/09",
            "10/10", "12/10", "14/10", "14/11", "03/12", "05/12", "05/12", "25/12"]
REQUIRED = {"data", "pilar", "fonte", "url", "checked_at", "verificada"}
# LACUNA: "memoria" nao esta nos pilares do plano:636, mas a tabela traz "memoria/bastidores".
PILARES = {"servico", "arrecadacao", "voluntariado", "prestacao de contas", "bastidores", "memoria"}


def _norm(text):
    text = unicodedata.normalize("NFKD", text.strip().casefold())
    text = text.replace("–", "-").replace("—", "-")
    return "".join(c for c in text if not unicodedata.combining(c))


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _row_ok(row):
    if not isinstance(row, dict) or not REQUIRED <= set(row):
        return False
    if not isinstance(row["verificada"], bool):
        return False
    if any(not isinstance(row[k], str) or not row[k].strip() for k in ("data", "pilar", "fonte", "url", "checked_at")):
        return False
    if not row["url"].strip().lower().startswith("http"):
        return False
    try:
        date.fromisoformat(row["checked_at"].strip())
    except ValueError:
        return False
    return all(_norm(p) in PILARES for p in str(row["pilar"]).split("/"))


def _stale(rows, on):
    ref = date.fromisoformat(on)
    return [r for r in rows if (ref - date.fromisoformat(r["checked_at"])).days > 90]


def test_data_has_15_rows_with_expected_days():
    rows = _load(DATA)
    assert Counter(_norm(r["data"]) for r in rows) == Counter(EXPECTED)

def test_data_schema_accepts_every_row():
    rows = _load(DATA)
    assert rows and all(_row_ok(r) for r in rows)


def test_data_stale_rule_is_90_days_with_injected_date(tmp_path):
    fx = tmp_path / "cal.json"
    fx.write_text(json.dumps([
        {"data": "01/01", "pilar": "servico", "fonte": "F", "url": "http://x", "checked_at": "2026-11-11",
         "verificada": True},
        {"data": "05/06", "pilar": "servico", "fonte": "F", "url": "http://x", "checked_at": "2027-02-01",
         "verificada": True}]), encoding="utf-8")
    rows = _load(fx)
    assert _stale(rows, "2027-02-08") == []
    assert [r["data"] for r in _stale(rows, "2027-02-10")] == ["01/01"]


def test_data_unverified_rows_say_nao_encontrei():
    rows = _load(DATA)
    assert sorted(_norm(r["data"]) for r in rows if r["verificada"] is False) == ["07/06", "10/10"]


def test_data_missing_file_fails_closed(tmp_path):
    with pytest.raises(FileNotFoundError):
        _load(tmp_path / "calendario-2027.json")


def test_data_truncated_json_fails_closed(tmp_path):
    bad = tmp_path / "cal.json"
    bad.write_text('{"data": "01/01",', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        _load(bad)


def test_data_wrong_row_type_rejected(tmp_path):
    bad = tmp_path / "cal.json"
    bad.write_text(json.dumps([{"data": "01/01"}, "linha-solta", 42]), encoding="utf-8")
    rows = _load(bad)
    assert rows and not all(_row_ok(r) for r in rows)
