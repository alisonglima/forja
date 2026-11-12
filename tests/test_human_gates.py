"""Contrato T-GATES-01: congela L-GATES-01 (plano:2584, teste plano:2621,
mapa plano:2573 run_review/run_approve; tabelas plano:426-427/451-452;
APPROVAL_STALE exit 1 plano:470/530; Step(ctx) steps.py:14-22.
# LACUNA: serializacao exata do hash agregado do lote e da chave approve v2.
# LACUNA: recomposicao exata do hash composto do brief c/ manifesto da marca.
"""
import hashlib
import json

import pytest


def _ctx(root):
    from forja import steps
    from pathlib import Path
    r = Path(root);(r / "work").mkdir(parents=True, exist_ok=True);(r / "out").mkdir(parents=True, exist_ok=True)
    return steps.Ctx(root=r, cfg={}, work=r / "work", out=r / "out", env={}, log=lambda m: None, dry_run=False)

def _w(p, d, b=False):
    from pathlib import Path
    q = Path(p);q.parent.mkdir(parents=True, exist_ok=True)
    q.write_bytes(d) if b else q.write_text(d, encoding="utf-8")

def _base(c, rel="out/peca.png", raw=b"ARTEDATA", dec="aprovado"):
    art = {"path": rel, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    _w(c.work / "inspect" / "peca.json", '{"ok": true}');_w(c.work / "render" / "peca.png", b"PNGDATA", True)
    _w(c.work / "review" / "peca.1280.aberta", "");_w(c.work / "review" / "peca.360.aberta", "")
    _w(c.work / "review" / "peca.json", json.dumps({"decisao": dec, "notas": "ok"}));_w(c.root / rel, raw, True)
    _w(c.root / "approvals.json", json.dumps({"schema_version": 2, "script": True, "voice": True, "overlays": True, "publish": False, "by": "Ana", "at": "2026-11-11T18:00:00Z", "piece": "peca", "brand_id": "b", "format": "ig-portrait", "artifacts": [art], "hash": {"algoritmo": "sha256", "valor": art["sha256"], "arquivo": rel, "bytes": art["bytes"]}}))
    return art["sha256"]

def test_review_aprovado_registra_decisao(tmp_path):
    from forja.workflows import human_gates
    c = _ctx(tmp_path);_base(c)
    assert human_gates.run_review(c)["decisao"] == "aprovado"
    assert json.loads((c.work / "review" / "peca.json").read_text(encoding="utf-8"))["decisao"] == "aprovado"

def test_review_sem_marcador_360_falha_gate(tmp_path):
    from forja.errors import ForjaError;from forja.workflows import human_gates
    c = _ctx(tmp_path);_base(c);(c.work / "review" / "peca.360.aberta").unlink()
    with pytest.raises(ForjaError) as e: human_gates.run_review(c)
    assert (e.value.code, e.value.exit_code) == ("GATE_FAILED", 1)

def test_review_decisao_invalida_falha_gate(tmp_path):
    from forja.errors import ForjaError;from forja.workflows import human_gates
    c = _ctx(tmp_path);_base(c)
    _w(c.work / "review" / "peca.json", json.dumps({"decisao": "talvez", "notas": "x"}))
    with pytest.raises(ForjaError) as e: human_gates.run_review(c)
    assert (e.value.code, e.value.exit_code) == ("GATE_FAILED", 1)

def test_review_sem_inspect_falha_gate(tmp_path):
    from forja.errors import ForjaError;from forja.workflows import human_gates
    c = _ctx(tmp_path);_base(c);(c.work / "inspect" / "peca.json").unlink()
    with pytest.raises(ForjaError) as e: human_gates.run_review(c)
    assert (e.value.code, e.value.exit_code) == ("GATE_FAILED", 1)

def test_review_json_truncado_falha_fechado(tmp_path):
    from forja.errors import ForjaError;from forja.workflows import human_gates
    c = _ctx(tmp_path);_base(c);_w(c.work / "review" / "peca.json", "{quebrado")
    with pytest.raises(ForjaError) as e: human_gates.run_review(c)
    assert e.value.code == "GATE_FAILED"

def test_approve_happy_valida_hash_e_grava(tmp_path):
    from forja.workflows import human_gates
    c = _ctx(tmp_path);s = _base(c);r = human_gates.run_approve(c)
    assert s in json.dumps(r) and s in (c.work / "approve.json").read_text(encoding="utf-8")

def test_approve_hash_divergente_vira_stale(tmp_path):
    from forja.errors import ForjaError;from forja.workflows import human_gates
    c = _ctx(tmp_path);_base(c);_w(c.root / "out" / "peca.png", b"TROCADA", True)
    with pytest.raises(ForjaError) as e: human_gates.run_approve(c)
    assert (e.value.code, e.value.exit_code) == ("APPROVAL_STALE", 1)

def test_approve_artefato_sumiu_vira_stale(tmp_path):
    from forja.errors import ForjaError;from forja.workflows import human_gates
    c = _ctx(tmp_path);_base(c);(c.root / "out" / "peca.png").unlink()
    with pytest.raises(ForjaError) as e: human_gates.run_approve(c)
    assert (e.value.code, e.value.exit_code) == ("APPROVAL_STALE", 1)

def test_approve_sem_review_aprovado_falha_gate(tmp_path):
    from forja.errors import ForjaError;from forja.workflows import human_gates
    c = _ctx(tmp_path);_base(c, dec="ajustes")
    with pytest.raises(ForjaError) as e: human_gates.run_approve(c)
    assert (e.value.code, e.value.exit_code) == ("GATE_FAILED", 1)

def test_approve_caminho_dotdot_falha_gate(tmp_path):
    from forja.errors import ForjaError;from forja.workflows import human_gates
    c = _ctx(tmp_path);_base(c, rel="../fora.png")
    with pytest.raises(ForjaError) as e: human_gates.run_approve(c)
    assert e.value.code == "GATE_FAILED"

def test_approve_tipo_errado_falha_gate(tmp_path):
    from forja.errors import ForjaError;from forja.workflows import human_gates
    c = _ctx(tmp_path);_base(c)
    bad = json.loads((c.root / "approvals.json").read_text(encoding="utf-8"));bad["hash"]["valor"] = 123
    _w(c.root / "approvals.json", json.dumps(bad))
    with pytest.raises(ForjaError) as e: human_gates.run_approve(c)
    assert e.value.code == "GATE_FAILED"

def test_approve_sem_approvals_falha_gate(tmp_path):
    from forja.errors import ForjaError;from forja.workflows import human_gates
    c = _ctx(tmp_path);_base(c);(c.root / "approvals.json").unlink()
    with pytest.raises(ForjaError) as e: human_gates.run_approve(c)
    assert e.value.code in ("GATE_FAILED", "APPROVAL_STALE")
