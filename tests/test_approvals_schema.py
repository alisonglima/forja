"""Contrato do formato approvals.json v2 (schema e preservacao em brief).

Fontes: plano:715 (v2), plano:797 (N-04) e DESIGN.md:512-528 (Z.1.1).
Congela: schema_version=2; booleanos; by/at; piece/brand_id/format; brief
{sha256,by,at}; artifacts [{path,sha256,bytes}]; hash {algoritmo,valor,
arquivo,bytes}, com arquivo omitido em lote/carrossel; removidos version/
brief_hash/approved_hash/hash_inputs; load/write preservam as chaves novas;
v1 sem schema_version continua legivel.
# LACUNA: contrato nao decide tipos v2 no load nem required de topo no schema.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

SCHEMA = Path(__file__).resolve().parents[1] / "forja" / "schemas" / "approvals.schema.json"

def _schema():
    return json.loads(SCHEMA.read_text(encoding="utf-8"))

def _write(root, data):
    (root / "approvals.json").write_text(json.dumps(data), encoding="utf-8")

def _v2():
    return {
        "schema_version": 2, "script": True, "voice": True, "overlays": False,
        "publish": False, "by": "Ana", "at": "2026-11-11T18:00:00Z",
        "piece": "post-dia-x", "brand_id": "leo-lions", "format": "ig-portrait",
        "brief": {"sha256": "a" * 64, "by": "Ana", "at": "2026-11-11T17:40:00Z"},
        "artifacts": [{"path": "out/post/feed.png", "sha256": "b" * 64, "bytes": 812345}],
        "hash": {"algoritmo": "sha256", "valor": "c" * 64,
                 "arquivo": "out/post/feed.png", "bytes": 812345},
    }

def test_schema_declares_v2_fields_and_types():
    schema = _schema()
    props = schema["properties"]
    assert schema["type"] == "object" and props["schema_version"]["const"] == 2
    kinds = {
        "schema_version": "integer", "script": "boolean", "voice": "boolean",
        "overlays": "boolean", "publish": "boolean", "by": "string", "at": "string",
        "piece": "string", "brand_id": "string", "format": "string",
        "brief": "object", "artifacts": "array", "hash": "object",
    }
    assert {name: props[name]["type"] for name in kinds} == kinds

def test_schema_requires_nested_hashes_and_bytes():
    props = _schema()["properties"]
    assert {"sha256", "by", "at"} <= set(props["brief"]["required"])
    assert {"path", "sha256", "bytes"} <= set(props["artifacts"]["items"]["required"])
    hashed = props["hash"]
    assert {"algoritmo", "valor", "bytes"} <= set(hashed["required"])
    assert "arquivo" in hashed["properties"] and "arquivo" not in hashed["required"]

def test_schema_does_not_declare_removed_v1_keys():
    schema = _schema()
    removed = ("version", "brief_hash", "approved_hash", "hash_inputs")
    assert not set(removed) & (set(schema["properties"]) | set(schema.get("required", [])))

def test_load_preserves_v2_extended_fields(tmp_path):
    from forja import brief
    data = _v2()
    _write(tmp_path, data)
    assert brief.load_approvals(tmp_path) == data

def test_write_merges_and_preserves_v2_extended_fields(tmp_path):
    from forja import brief
    data = _v2()
    _write(tmp_path, data)
    now = datetime.datetime(2026, 11, 11, 19, 0, tzinfo=datetime.timezone.utc)
    written = brief.write_approvals(tmp_path, {"publish": True}, by="Bia", now=now)
    assert [written[k] for k in ("script", "voice", "overlays", "publish")] == [
        True, True, False, True]
    assert (written["by"], written["at"]) == ("Bia", "2026-11-11T19:00:00Z")
    for key in ("schema_version", "piece", "brand_id", "format", "brief", "artifacts", "hash"):
        assert written[key] == data[key]
    assert json.loads((tmp_path / "approvals.json").read_text(encoding="utf-8")) == written

def test_v1_and_missing_approvals_keep_legacy_defaults(tmp_path):
    from forja import brief
    loaded = brief.load_approvals(tmp_path)
    assert [loaded[k] for k in ("script", "voice", "overlays", "publish")] == [False] * 4
    assert (loaded["by"], loaded["at"]) == ("", "")
    _write(tmp_path, {"script": True, "voice": False, "overlays": False,
                      "publish": False, "by": "Ana", "at": "2026-11-11T18:00:00Z"})
    loaded = brief.load_approvals(tmp_path)
    assert [loaded[k] for k in ("script", "voice", "overlays", "publish")] == [
        True, False, False, False]
    assert (loaded["by"], loaded["at"]) == ("Ana", "2026-11-11T18:00:00Z")

def test_truncated_approvals_json_fails_closed(tmp_path):
    from forja import brief
    from forja.errors import ForjaError
    (tmp_path / "approvals.json").write_text('{"script": true', encoding="utf-8")
    with pytest.raises(ForjaError) as excinfo:
        brief.load_approvals(tmp_path)
    assert excinfo.value.code == "GATE_FAILED"
