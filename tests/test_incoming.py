"""Contrato de ingestao de incoming/ (lane T-IN-01; congela N-27).
plano:758 origem/conta/ferramenta/prompt/data/synthid/c2pa/elementos_ia/licenca/sha256; bytes nunca reescritos; hash divergente vira erro; manual exige licenca; ausentes viram INCOMING_INCOMPLETE.
plano:779 scan_incoming(root)->list[dict]; ingest(root, asset, sidecar)->dict.
plano:438 manifesto incoming/manifest.json schema incoming/v1; item com id/arquivo/sha256/bytes/origem/conta/ferramenta/prompt/data/synthid/c2pa/license/uso/destino.
plano:2455(Z.1#14) sidecars *.meta.json opcionais fundidos no canonico; assets.py le so ele.
plano:1288-1297 SynthID/C2PA reais nao verificados; teste usa bytes sinteticos.
LACUNA: ai_studio (758) x ai-studio (438); shapes de license/synthid/c2pa/elementos_ia, codigos de hash/manual, tipos dos args e chaves do manifesto nao decididos; conta 1/2 sem tipo, teste usa int.
"""
import hashlib
import json

import pytest


def _write_asset(root, name="foto.png", data=b"bytes-sinteticos-1"):
    asset = root / "incoming" / name
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(data)
    return asset


def _write_sidecar(asset, meta):
    sidecar = asset.parent / (asset.name + ".meta.json")
    sidecar.write_text(json.dumps(meta), encoding="utf-8")
    return sidecar


def _meta(sha256, **over):
    meta = {"origem": "flow", "conta": 1, "ferramenta": "flow-imagem",
            "prompt": "cartaz do leao", "data": "2026-11-11",
            "synthid": {"presente": True}, "c2pa": {"presente": True, "assertion": "abc"},
            "elementos_ia": ["imagem-gerada"], "license": "uso-editorial", "sha256": sha256}
    meta.update(over)
    return meta


def test_ingest_happy_path_registers_sha256_and_manifest(tmp_path):
    from forja import incoming

    asset = _write_asset(tmp_path)
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    sidecar = _write_sidecar(asset, _meta(digest))
    out = incoming.ingest(tmp_path, asset, sidecar)
    assert (out["sha256"], out["origem"], out["conta"]) == (digest, "flow", 1)
    assert out["bytes"] == len(asset.read_bytes())
    raw = (tmp_path / "incoming" / "manifest.json").read_text(encoding="utf-8")
    assert digest in raw and "incoming/v1" in raw


def test_scan_happy_path_reports_no_incoming_incomplete(tmp_path):
    from forja import incoming

    asset = _write_asset(tmp_path)
    _write_sidecar(asset, _meta(hashlib.sha256(asset.read_bytes()).hexdigest()))
    issues = incoming.scan_incoming(tmp_path)
    assert isinstance(issues, list)
    assert [i["code"] for i in issues].count("INCOMING_INCOMPLETE") == 0


@pytest.mark.parametrize("campo", ["origem", "conta", "ferramenta", "data"])
def test_scan_campo_obrigatorio_ausente_reports_incoming_incomplete(tmp_path, campo):
    from forja import incoming

    asset = _write_asset(tmp_path)
    meta = _meta(hashlib.sha256(asset.read_bytes()).hexdigest())
    del meta[campo]
    _write_sidecar(asset, meta)
    assert "INCOMING_INCOMPLETE" in [i["code"] for i in incoming.scan_incoming(tmp_path)]


def test_ingest_manual_without_license_is_error(tmp_path):
    from forja import incoming

    asset = _write_asset(tmp_path)
    meta = _meta(hashlib.sha256(asset.read_bytes()).hexdigest(), origem="manual")
    del meta["license"]
    with pytest.raises(Exception):
        incoming.ingest(tmp_path, asset, _write_sidecar(asset, meta))


def test_ingest_sidecar_hash_mismatch_is_error(tmp_path):
    from forja import incoming

    asset = _write_asset(tmp_path)
    sidecar = _write_sidecar(asset, _meta("0" * 64))
    with pytest.raises(Exception):
        incoming.ingest(tmp_path, asset, sidecar)


def test_ingest_never_rewrites_asset_bytes(tmp_path):
    from forja import incoming

    asset = _write_asset(tmp_path)
    before = asset.read_bytes()
    sidecar = _write_sidecar(asset, _meta(hashlib.sha256(before).hexdigest()))
    incoming.ingest(tmp_path, asset, sidecar)
    assert asset.read_bytes() == before


def test_scan_empty_incoming_returns_empty_list(tmp_path):
    from forja import incoming

    (tmp_path / "incoming").mkdir()
    assert incoming.scan_incoming(tmp_path) == []


def test_scan_without_incoming_dir_returns_empty_list(tmp_path):
    from forja import incoming
    assert incoming.scan_incoming(tmp_path) == []


def test_ingest_dotdot_asset_path_is_rejected(tmp_path):
    from forja import incoming

    asset = _write_asset(tmp_path)
    (tmp_path / "fora.png").write_bytes(b"fora")
    sidecar = _write_sidecar(asset, _meta(hashlib.sha256(asset.read_bytes()).hexdigest()))
    with pytest.raises(Exception):
        incoming.ingest(tmp_path, asset.parent / ".." / "fora.png", sidecar)


def test_ingest_truncated_sidecar_json_is_error(tmp_path):
    from forja import incoming

    asset = _write_asset(tmp_path)
    sidecar = asset.parent / (asset.name + ".meta.json")
    sidecar.write_text('{"origem": "flow", "conta":', encoding="utf-8")
    with pytest.raises(Exception):
        incoming.ingest(tmp_path, asset, sidecar)


def test_ingest_sidecar_wrong_type_is_error(tmp_path):
    from forja import incoming

    asset = _write_asset(tmp_path)
    sidecar = _write_sidecar(asset, ["nao-um-objeto"])
    with pytest.raises(Exception):
        incoming.ingest(tmp_path, asset, sidecar)
