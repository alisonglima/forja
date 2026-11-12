"""Contrato APPROVAL_STALE em forja/brief.py (N-06; congela L-APR-STALE-01).
Congela require_approvals(..., piece_hash=None) + write/load preservando v2
(plano:799); APPROVAL_STALE exit 1 retryable false p/ hash/brief mudou ou
arquivo sumiu (plano:470); v1 sem hash so vale p/ dub/storyboard, post exige
hash+artifacts e volta a render_pendente (plano:510-543); details expected /
current (plano:710-719; LACUNA: piece x path); formato v2 (plano:1385-1400).
"""
import json

import pytest

_STORED = "ab" * 32
_OTHER = "cd" * 32

def _cfg():
    return {"project": {"require_approvals": True}}

def _wj(root, data):
    (root / "approvals.json").write_text(json.dumps(data), encoding="utf-8")

def _v2(v=_STORED, p="out/post/feed.png"):
    return {"schema_version": 2, "script": True, "voice": True, "overlays": False, "publish": False, "by": "Ana", "at": "2026-11-11T18:00:00Z", "piece": "post-dia-x", "brand_id": "leo-lions", "format": "ig-portrait", "brief": {"sha256": "ef" * 32, "by": "Ana", "at": "2026-11-11T17:40:00Z"}, "artifacts": [{"path": p, "sha256": v, "bytes": 8}], "hash": {"algoritmo": "sha256", "valor": v, "arquivo": p, "bytes": 8}}

def test_matching_piece_hash_passes(tmp_path):
    from forja import brief
    _wj(tmp_path, _v2())
    (tmp_path / "out" / "post").mkdir(parents=True)
    (tmp_path / "out" / "post" / "feed.png").write_bytes(b"pngbytes")
    brief.require_approvals(tmp_path, _cfg(), ("script", "voice"), piece_hash=_STORED)

def test_mismatched_piece_hash_is_stale(tmp_path):
    from forja import brief
    from forja.errors import ForjaError
    _wj(tmp_path, _v2())
    with pytest.raises(ForjaError) as e:
        brief.require_approvals(tmp_path, _cfg(), ("script", "voice"), piece_hash=_OTHER)
    assert e.value.code == "APPROVAL_STALE"
    assert e.value.exit_code == 1 and e.value.retryable is False
    assert (e.value.details["expected"], e.value.details["current"]) == (_STORED, _OTHER)
    # LACUNA: plano:710-719 details={expected,current,piece}; plano:485-509 {expected,current,path}.

def test_v1_without_hash_is_stale_when_piece_hash_given(tmp_path):
    from forja import brief
    from forja.errors import ForjaError
    _wj(tmp_path, {"script": True, "voice": True, "by": "Ana", "at": "2026-11-11T18:00:00Z"})
    with pytest.raises(ForjaError) as e:
        brief.require_approvals(tmp_path, _cfg(), ("script", "voice"), piece_hash=_STORED)
    assert e.value.code == "APPROVAL_STALE" and e.value.exit_code == 1

def test_legacy_gate_without_piece_hash_still_passes(tmp_path):
    from forja import brief
    _wj(tmp_path, {"script": True, "voice": True, "by": "Ana", "at": "2026-11-11T18:00:00Z"})
    brief.require_approvals(tmp_path, _cfg(), ("script", "voice"))

def test_missing_approvals_file_with_piece_hash_fails_closed(tmp_path):
    from forja import brief
    from forja.errors import ForjaError
    with pytest.raises(ForjaError) as e:
        brief.require_approvals(tmp_path, _cfg(), ("script", "voice"), piece_hash=_STORED)
    assert e.value.code == "APPROVAL_STALE" and e.value.exit_code == 1

def test_approved_file_missing_is_stale(tmp_path):
    from forja import brief
    from forja.errors import ForjaError
    _wj(tmp_path, _v2())
    with pytest.raises(ForjaError) as e:
        brief.require_approvals(tmp_path, _cfg(), ("script", "voice"), piece_hash=_STORED)
    assert e.value.code == "APPROVAL_STALE" and e.value.exit_code == 1

def test_v2_keys_survive_load_and_write(tmp_path):
    import datetime
    from forja import brief
    _wj(tmp_path, _v2())
    loaded = brief.load_approvals(tmp_path)
    assert loaded["schema_version"] == 2 and loaded["piece"] == "post-dia-x"
    assert loaded["hash"]["valor"] == _STORED and loaded["brief"]["sha256"] == "ef" * 32
    now = datetime.datetime(2026, 11, 11, 18, 0, 0, tzinfo=datetime.timezone.utc)
    data = brief.write_approvals(tmp_path, {"voice": True}, by="Ana", now=now)
    assert data["schema_version"] == 2 and data["hash"]["valor"] == _STORED
    assert data["artifacts"][0]["path"] == "out/post/feed.png"

def test_parent_path_in_hash_is_stale_and_stays_inside_root(tmp_path):
    from forja import brief
    from forja.errors import ForjaError
    _wj(tmp_path, _v2(p="../fora.png"))
    with pytest.raises(ForjaError) as e:
        brief.require_approvals(tmp_path, _cfg(), ("script", "voice"), piece_hash=_STORED)
    assert e.value.code == "APPROVAL_STALE"
    assert not (tmp_path.parent / "fora.png").exists()

def test_truncated_approvals_json_fails_closed(tmp_path):
    from forja import brief
    from forja.errors import ForjaError
    (tmp_path / "approvals.json").write_text("{quebrado", encoding="utf-8")
    with pytest.raises(ForjaError) as e:
        brief.require_approvals(tmp_path, _cfg(), ("script", "voice"), piece_hash=_STORED)
    assert e.value.code in ("APPROVAL_STALE", "GATE_FAILED") and e.value.exit_code == 1
    # LACUNA: contrato nao decide entre APPROVAL_STALE e GATE_FAILED p/ JSON truncado com piece_hash.

def test_wrong_type_hash_value_is_stale(tmp_path):
    from forja import brief
    from forja.errors import ForjaError
    bad = _v2()
    bad["hash"]["valor"] = 123
    _wj(tmp_path, bad)
    with pytest.raises(ForjaError) as e:
        brief.require_approvals(tmp_path, _cfg(), ("script", "voice"), piece_hash=_STORED)
    assert e.value.code == "APPROVAL_STALE"
