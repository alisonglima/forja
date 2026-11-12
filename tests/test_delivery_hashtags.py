"""Contrato: aviso de hashtag fora da lista canonica (so avisos, nunca bloqueia)."""
import hashlib
import shutil
from pathlib import Path

NOW = "2026-11-12T18:00:00Z"
ARTE = b"arte-bytes-123"
HASHTAGS = Path(__file__).resolve().parents[1] / "brands" / "leo-lions" / "hashtags.json"


def _base(root, hashtags=None, com_hashtags=True, **brief_extra):
    src = root / "out" / "post" / "feed.png"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(ARTE)
    sha = hashlib.sha256(ARTE).hexdigest()
    brand = root / "brand"
    brand.mkdir(parents=True, exist_ok=True)
    (brand / "manifest.json").write_text('{"id": "leo-lions"}', encoding="utf-8")
    if com_hashtags:
        shutil.copyfile(HASHTAGS, brand / "hashtags.json")
    brief = {"piece": "post-dia-x", "brand_id": "leo-lions", "format": "ig-feed-4x5",
             "legenda": "Legenda curta da peca.", "hashtags": hashtags or ["WeServe"],
             "alt": "Voluntarios plantam arvores", "arte": "out/post/feed.png",
             "horario": {"sugestao": "18:00", "fuso": "America/Sao_Paulo"}}
    brief.update(brief_extra)
    formats = {"ig-feed-4x5": {"max_hashtags": 5, "alt_max": 100, "max_chars": 2200}}
    approvals = {"schema_version": 2, "by": "Ana", "at": NOW, "piece": "post-dia-x",
                 "brand_id": "leo-lions", "format": "ig-feed-4x5",
                 "brief": {"sha256": "0" * 64, "by": "Ana", "at": NOW},
                 "artifacts": [{"path": "out/post/feed.png", "sha256": sha, "bytes": len(ARTE)}],
                 "hash": {"algoritmo": "sha256", "valor": sha, "arquivo": "out/post/feed.png",
                          "bytes": len(ARTE)}}
    return brief, brand, formats, approvals


def _run(root, **kw):
    from forja import delivery
    brief, brand, formats, approvals = _base(root, **kw)
    return delivery.build_package(root, brief=brief, brand_root=brand, formats=formats,
                                  approvals=approvals, now=NOW)


def test_tag_na_lista_sem_aviso(tmp_path):
    from forja import delivery  # noqa: F401
    for i, tag in enumerate(["WeServe", "weserve", "#WeServe"]):
        m = _run(tmp_path / str(i), hashtags=[tag])
        assert m["avisos"] == []


def test_tag_fora_da_lista_avisa_uma_vez(tmp_path):
    from forja import delivery  # noqa: F401
    m = _run(tmp_path / "a", hashtags=["promocaodomes"])
    assert m["avisos"] == ["HASHTAG_FORA_DA_LISTA"]
    m = _run(tmp_path / "b", hashtags=["promocaodomes", "festadobairro"])
    assert m["avisos"] == ["HASHTAG_FORA_DA_LISTA"]


def test_tag_generica_avisa_generica(tmp_path):
    from forja import delivery  # noqa: F401
    m = _run(tmp_path, hashtags=["FYP"])
    assert m["avisos"] == ["HASHTAG_GENERICA"]


def test_sem_hashtags_json_sem_aviso(tmp_path):
    from forja import delivery  # noqa: F401
    m = _run(tmp_path, hashtags=["promocaodomes", "FYP"], com_hashtags=False)
    assert m["avisos"] == []


def test_avisos_convivem_com_consent_pending(tmp_path):
    from forja import delivery  # noqa: F401
    m = _run(tmp_path, hashtags=["promocaodomes"], pessoas=True)
    assert m["avisos"] == ["BRIEF_CONSENT_PENDING", "HASHTAG_FORA_DA_LISTA"]


def test_pacote_criado_e_hashtags_txt(tmp_path):
    from forja import delivery  # noqa: F401
    m = _run(tmp_path, hashtags=["promocaodomes", "FYP"])
    assert "HASHTAG_FORA_DA_LISTA" in m["avisos"]
    assert "HASHTAG_GENERICA" in m["avisos"]
    txt = (tmp_path / "entrega" / "hashtags.txt").read_text(encoding="utf-8")
    assert txt == "#promocaodomes #FYP"
