"""Contrato de hash de aprovacoes (congela N-03 `L-APR-HASH-01`).
plano:714: `hash_brief` = SHA-256 de `brief.yaml` normalizado + `brands/<id>/manifest.json` + piece/brand_id/format.
plano:714: `hash_piece` = `hash_brief` + cada artefato de `out/` (relpath, tamanho, sha256), em lista ordenada.
plano:714: exclui `approvals.json`, `by`, `at`, mtime e abs paths; saida 64 hex; deterministico, ordem-independente.
plano:762: `forja.approvals`: `hash_brief(root)`, `hash_piece(root)`, `hash_files(paths, extra=None)`; `APPROVAL_VERSION = 2`.
plano:796: implementacao em `forja/approvals.py` (NOVO); este teste e a prova aceita.
"""
import os
import re

import pytest


def _proj(root, piece="p1", brand="leo", fmt="clip"):
    (root / "brief.yaml").write_text(f"piece: {piece}\nbrand_id: {brand}\nformat: {fmt}\n", encoding="utf-8")
    d = root / "brands" / brand
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text('{"id": "%s"}' % brand, encoding="utf-8")
    return root

def _art(root, name, data=b"xyz"):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p

def test_approval_version_is_two():
    from forja import approvals
    assert approvals.APPROVAL_VERSION == 2

def test_hash_brief_returns_64_hex(tmp_path):
    from forja import approvals
    assert re.fullmatch(r"[0-9a-f]{64}", approvals.hash_brief(_proj(tmp_path)))

def test_hash_piece_returns_64_hex(tmp_path):
    from forja import approvals
    _art(_proj(tmp_path), "out/a.mp4")
    assert re.fullmatch(r"[0-9a-f]{64}", approvals.hash_piece(tmp_path))

def test_hash_files_mixes_paths_and_extra(tmp_path):
    from forja import approvals
    a, b = _art(tmp_path, "a.bin", b"1"), _art(tmp_path, "b.bin", b"22")
    assert approvals.hash_files([a, b]) == approvals.hash_files([b, a])
    assert approvals.hash_files([a], extra="v2") != approvals.hash_files([a])
    # LACUNA: tipo/semantica de `extra` nao definidos (plano:762 so da a assinatura).

def test_hash_brief_ignores_absolute_location(tmp_path):
    from forja import approvals
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    assert approvals.hash_brief(_proj(a)) == approvals.hash_brief(_proj(b))

def test_hash_brief_normalizes_trailing_newline(tmp_path):
    from forja import approvals
    h1 = approvals.hash_brief(_proj(tmp_path))
    text = (tmp_path / "brief.yaml").read_text(encoding="utf-8")
    (tmp_path / "brief.yaml").write_text(text.rstrip("\n"), encoding="utf-8")
    assert approvals.hash_brief(tmp_path) == h1
    # LACUNA: algoritmo de normalizacao nao detalhado (plano:714); pinada so a invariancia basica.

def test_hash_brief_covers_manifest_and_piece_fields(tmp_path):
    from forja import approvals
    h0 = approvals.hash_brief(_proj(tmp_path))
    (tmp_path / "brands" / "leo" / "manifest.json").write_text('{"id": "leo2"}', encoding="utf-8")
    assert approvals.hash_brief(tmp_path) != h0
    (tmp_path / "brief.yaml").write_text("piece: p2\nbrand_id: leo\nformat: still\n", encoding="utf-8")
    (tmp_path / "brands" / "leo" / "manifest.json").write_text('{"id": "leo"}', encoding="utf-8")
    assert approvals.hash_brief(tmp_path) != h0

def test_hash_brief_ignores_approvals_and_mtime(tmp_path):
    from forja import approvals
    h0 = approvals.hash_brief(_proj(tmp_path))
    (tmp_path / "approvals.json").write_text('{"script": true, "by": "Ana", "at": "x"}', encoding="utf-8")
    assert approvals.hash_brief(tmp_path) == h0
    os.utime(tmp_path / "brief.yaml", (1, 1))
    assert approvals.hash_brief(tmp_path) == h0

def test_hash_piece_covers_artifacts(tmp_path):
    from forja import approvals
    _art(_proj(tmp_path), "out/a.mp4", b"1")
    h0 = approvals.hash_piece(tmp_path)
    _art(tmp_path, "out/a.mp4", b"222")
    assert approvals.hash_piece(tmp_path) != h0
    # LACUNA: semantica de `out/` vazio/ausente nao decidida (plano:714 lista so artefatos presentes).

def test_hash_piece_orders_artifacts(tmp_path):
    from forja import approvals
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    _art(_proj(a), "out/1.mp4", b"x")
    _art(a, "out/2.mp4", b"y")
    _art(_proj(b), "out/2.mp4", b"y")
    _art(b, "out/1.mp4", b"x")
    assert approvals.hash_piece(a) == approvals.hash_piece(b)

def test_hash_brief_missing_input_raises(tmp_path):
    from forja import approvals
    with pytest.raises(Exception):
        approvals.hash_brief(tmp_path)
    _proj(tmp_path)
    (tmp_path / "brief.yaml").write_text("", encoding="utf-8")
    with pytest.raises(Exception):
        approvals.hash_brief(tmp_path)
    # LACUNA: sem codigo de erro nomeado para o hash (APPROVAL_STALE e de L-ERR-01); exige-se so falha fechada.

def test_hash_brief_rejects_hostile_inputs(tmp_path):
    from forja import approvals
    _proj(tmp_path)
    (tmp_path / "brands" / "leo" / "manifest.json").write_text('{"id": tru', encoding="utf-8")
    with pytest.raises(Exception):
        approvals.hash_brief(tmp_path)
    (tmp_path / "brief.yaml").write_text("piece: p1\nbrand_id: ../evil\nformat: clip\n", encoding="utf-8")
    with pytest.raises(Exception):
        approvals.hash_brief(tmp_path)
