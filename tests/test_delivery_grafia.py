"""Contrato: grafia LEO aplicada na entrega (legenda, alt, hashtags) quando a marca traz grafia.json."""
import hashlib
import json
import shutil
from pathlib import Path

import pytest

NOW = "2026-11-12T18:00:00Z"
ARTE = b"arte-bytes-123"
GRAFIA = Path(__file__).resolve().parents[1] / "brands" / "leo-lions" / "grafia.json"


def _base(root, legenda="Legenda curta da peca.", com_grafia=True, **brief_extra):
    src = root / "out" / "post" / "feed.png"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(ARTE)
    sha = hashlib.sha256(ARTE).hexdigest()
    brand = root / "brand"
    brand.mkdir(parents=True, exist_ok=True)
    (brand / "manifest.json").write_text('{"id": "leo-lions"}', encoding="utf-8")
    if com_grafia:
        shutil.copyfile(GRAFIA, brand / "grafia.json")
    brief = {"piece": "post-dia-x", "brand_id": "leo-lions", "format": "ig-feed-4x5", "legenda": legenda,
             "hashtags": ["lions", "leo"], "alt": "Voluntarios plantam arvores", "arte": "out/post/feed.png",
             "horario": {"sugestao": "18:00", "fuso": "America/Sao_Paulo"}}
    brief.update(brief_extra)
    formats = {"ig-feed-4x5": {"max_hashtags": 5, "alt_max": 100, "max_chars": 2200}}
    approvals = {"schema_version": 2, "by": "Ana", "at": NOW, "piece": "post-dia-x", "brand_id": "leo-lions",
                 "format": "ig-feed-4x5", "brief": {"sha256": "0" * 64, "by": "Ana", "at": NOW},
                 "artifacts": [{"path": "out/post/feed.png", "sha256": sha, "bytes": len(ARTE)}],
                 "hash": {"algoritmo": "sha256", "valor": sha, "arquivo": "out/post/feed.png", "bytes": len(ARTE)}}
    return brief, brand, formats, approvals


def _run(root, **kw):
    from forja import delivery
    brief, brand, formats, approvals = _base(root, **kw)
    return delivery.build_package(root, brief=brief, brand_root=brand, formats=formats, approvals=approvals, now=NOW)


def test_erro_de_grafia_bloqueia(tmp_path):
    from forja.errors import ForjaError
    with pytest.raises(ForjaError) as exc:
        _run(tmp_path, legenda="Os Leos de Taquaritinga participaram.")
    assert exc.value.code == "GATE_FAILED"
    assert exc.value.details["campo"] == "grafia" and exc.value.details["codigo"] == "GRAFIA_LEO"
    assert exc.value.details["trecho"] == "Leos"


def test_erro_no_alt_e_nas_hashtags_bloqueia(tmp_path):
    from forja.errors import ForjaError
    with pytest.raises(ForjaError) as exc:
        _run(tmp_path, alt="Os Leos plantam arvores")
    assert exc.value.code == "GATE_FAILED"
    with pytest.raises(ForjaError) as exc:
        _run(tmp_path / "b", hashtags=["Leoísmo", "lions"])
    assert exc.value.details["codigo"] == "GRAFIA_LEO_DERIVADO"


def test_texto_correto_passa_sem_avisos(tmp_path):
    m = _run(tmp_path, legenda="Os LEOs do LEO Clube de Taquaritinga celebram o Dia Nacional do LEOísmo.")
    assert m["avisos"] == []


def test_aviso_nao_bloqueia_e_vai_ao_manifesto(tmp_path):
    m = _run(tmp_path, legenda="Encontro do Clube de LEOs de Taquaritinga.")
    assert m["avisos"] == ["GRAFIA_LEO_NOME"]


def test_avisos_somam_com_consentimento(tmp_path):
    m = _run(tmp_path, legenda="Encontro do Clube de LEOs.", pessoas=True)
    assert m["avisos"] == ["BRIEF_CONSENT_PENDING", "GRAFIA_LEO_NOME"]


def test_sem_grafia_json_na_marca_nao_verifica(tmp_path):
    m = _run(tmp_path, legenda="Os Leos participaram.", com_grafia=False)
    assert m["avisos"] == []


def test_outro_idioma_nao_verifica(tmp_path):
    m = _run(tmp_path, legenda="The Leos took part.", idioma="en")
    assert m["avisos"] == []
