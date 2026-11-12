"""Pacote entrega p/ Business Suite (humano agenda; estudio nao publica).
Contrato plano:754: entrega/ arte+sha256, legenda/hashtags(limite linha),
alt<=100, horario.json(sugestao+fuso), manifesto-ia.json(origem,ferramenta,
conta,prompt,data,synthid/c2pa,rotulo), manifesto.json(hashes,formato,
aprovador,hash.valor Z.1.1 plano:528/plano:2465). Recusa APPROVAL_STALE e
formato desconhecido. Assinatura plano:778 build_package(...)->dict; N-26
plano:850/plano:818. LACUNA: codigo p/ alt/hashtags/rotulo acima do limite
nao nomeado; hash.valor so copiado de approvals, sem recomputo aqui."""
import hashlib
import json

import pytest

NOW = "2026-11-11T18:00:00Z"
ARTE = b"arte-bytes-123"

def _base(root, hashtags=None, alt=None, rotulo=True, manifest_ok=True, fmt_max=2):
    src = root / "out" / "post" / "feed.png"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(ARTE)
    sha = hashlib.sha256(ARTE).hexdigest()
    brand = root / "brand"
    brand.mkdir(parents=True, exist_ok=True)
    (brand / "manifest.json").write_text('{"id": "leo-lions"}' if manifest_ok else '{"id":', encoding="utf-8")
    brief = {"piece": "post-dia-x", "brand_id": "leo-lions", "format": "ig-feed-4x5", "legenda": "Legenda curta da peca.", "hashtags": hashtags if hashtags is not None else ["lions", "leo"], "alt": alt if alt is not None else "Voluntarios em acao.", "horario": {"sugestao": "2026-11-12T18:00:00-03:00", "fuso": "America/Sao_Paulo"}, "arte": "out/post/feed.png", "elementos_ia": [{"origem": "fluxo", "ferramenta": "flow", "conta": "conta1", "prompt": "foto voluntarios", "data": "2026-11-10", "synthid": True, "c2pa": False, "rotulo": {"exigido": False} if rotulo else None}]}
    formats = {"ig-feed-4x5": {"max_hashtags": fmt_max, "alt_max": 100, "max_chars": 2200}}
    approvals = {"schema_version": 2, "by": "Ana", "at": NOW, "piece": "post-dia-x", "brand_id": "leo-lions", "format": "ig-feed-4x5", "brief": {"sha256": "0" * 64, "by": "Ana", "at": NOW}, "artifacts": [{"path": "out/post/feed.png", "sha256": sha, "bytes": len(ARTE)}], "hash": {"algoritmo": "sha256", "valor": sha, "arquivo": "out/post/feed.png", "bytes": len(ARTE)}}
    return brief, brand, formats, approvals

def test_happy_builds_entrega(tmp_path):
    from forja import delivery
    brief, brand, formats, approvals = _base(tmp_path)
    res = delivery.build_package(tmp_path, brief=brief, brand_root=brand, formats=formats, approvals=approvals, now=NOW)
    ent = tmp_path / "entrega"
    assert isinstance(res, dict)
    assert (ent / "arte" / "feed.png").read_bytes() == ARTE
    assert (ent / "legenda.txt").read_text(encoding="utf-8") == brief["legenda"]
    assert (ent / "alt.txt").read_text(encoding="utf-8") == brief["alt"]
    assert all(t in (ent / "hashtags.txt").read_text(encoding="utf-8") for t in brief["hashtags"])
    hor = json.loads((ent / "horario.json").read_text(encoding="utf-8"))
    assert hor["sugestao"] == brief["horario"]["sugestao"] and hor["fuso"] == brief["horario"]["fuso"]
    mia = json.loads((ent / "manifesto-ia.json").read_text(encoding="utf-8"))
    assert mia["elementos_ia"][0]["prompt"] == "foto voluntarios"
    assert mia["elementos_ia"][0]["rotulo"] == {"exigido": False}
    assert mia["elementos_ia"][0]["synthid"] is True and mia["elementos_ia"][0]["c2pa"] is False
    man = json.loads((ent / "manifesto.json").read_text(encoding="utf-8"))
    assert man["hash"]["valor"] == approvals["hash"]["valor"]
    assert "ig-feed-4x5" in (ent / "manifesto.json").read_text(encoding="utf-8")

def test_stale_hash_mismatch(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    brief, brand, formats, approvals = _base(tmp_path)
    approvals["hash"]["valor"] = "f" * 64
    with pytest.raises(ForjaError) as exc:
        delivery.build_package(tmp_path, brief=brief, brand_root=brand, formats=formats, approvals=approvals, now=NOW)
    assert exc.value.code == "APPROVAL_STALE"

def test_missing_approvals_is_stale(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    brief, brand, formats, _approvals = _base(tmp_path)
    with pytest.raises(ForjaError) as exc:
        delivery.build_package(tmp_path, brief=brief, brand_root=brand, formats=formats, approvals={}, now=NOW)
    assert exc.value.code == "APPROVAL_STALE"

def test_unknown_format(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    brief, brand, formats, approvals = _base(tmp_path)
    brief["format"] = "xx-desconhecido"
    with pytest.raises(ForjaError) as exc:
        delivery.build_package(tmp_path, brief=brief, brand_root=brand, formats=formats, approvals=approvals, now=NOW)
    assert exc.value.code == "FORMAT_UNSUPPORTED"

def test_alt_over_limit(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    brief, brand, formats, approvals = _base(tmp_path, alt="x" * 101)
    with pytest.raises(ForjaError):
        delivery.build_package(tmp_path, brief=brief, brand_root=brand, formats=formats, approvals=approvals, now=NOW)

def test_hashtags_over_limit(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    brief, brand, formats, approvals = _base(tmp_path, hashtags=["a", "b", "c"])
    with pytest.raises(ForjaError):
        delivery.build_package(tmp_path, brief=brief, brand_root=brand, formats=formats, approvals=approvals, now=NOW)

def test_ia_without_rotulo(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    brief, brand, formats, approvals = _base(tmp_path, rotulo=False)
    with pytest.raises(ForjaError):
        delivery.build_package(tmp_path, brief=brief, brand_root=brand, formats=formats, approvals=approvals, now=NOW)

def test_empty_brief(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    _brief, brand, formats, approvals = _base(tmp_path)
    with pytest.raises(ForjaError):
        delivery.build_package(tmp_path, brief={}, brand_root=brand, formats=formats, approvals=approvals, now=NOW)

def test_traversal_refused(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    brief, brand, formats, approvals = _base(tmp_path)
    brief["arte"] = "../evil.png"
    with pytest.raises(ForjaError):
        delivery.build_package(tmp_path, brief=brief, brand_root=brand, formats=formats, approvals=approvals, now=NOW)
    assert not (tmp_path / "evil.png").exists()

def test_truncated_brand_json(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    brief, brand, formats, approvals = _base(tmp_path, manifest_ok=False)
    with pytest.raises(ForjaError):
        delivery.build_package(tmp_path, brief=brief, brand_root=brand, formats=formats, approvals=approvals, now=NOW)

def test_wrong_type_hashtags(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    brief, brand, formats, approvals = _base(tmp_path, hashtags="#lions")
    with pytest.raises(ForjaError):
        delivery.build_package(tmp_path, brief=brief, brand_root=brand, formats=formats, approvals=approvals, now=NOW)

def test_only_contract_files(tmp_path):
    from forja import delivery
    brief, brand, formats, approvals = _base(tmp_path)
    delivery.build_package(tmp_path, brief=brief, brand_root=brand, formats=formats, approvals=approvals, now=NOW)
    names = sorted(p.name for p in (tmp_path / "entrega").iterdir())
    assert names == ["alt.txt", "arte", "hashtags.txt", "horario.json", "legenda.txt", "manifesto-ia.json", "manifesto.json"]
