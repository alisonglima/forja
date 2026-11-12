"""Contrato das regras de entrega vindas dos videos oficiais (T-ENTREGA-BP-01)."""
from __future__ import annotations
import hashlib
import json
import pytest
NOW = "2026-11-11T18:00:00Z"
ARTE = b"arte-bytes-123"
def _base(root, hashtags=None, alt=None, fmt_extra=None, brief_extra=None):
    src = root / "out" / "post" / "feed.png"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(ARTE)
    sha = hashlib.sha256(ARTE).hexdigest()
    brand = root / "brand"
    brand.mkdir(parents=True, exist_ok=True)
    (brand / "manifest.json").write_text('{"id": "leo-lions"}', encoding="utf-8")
    brief = {"piece": "post-dia-x", "brand_id": "leo-lions", "format": "ig-feed-4x5", "legenda": "Legenda curta da peca.", "hashtags": hashtags if hashtags is not None else ["lions", "leo"], "alt": alt if alt is not None else "Voluntarios em acao.", "horario": {"sugestao": "2026-11-12T18:00:00-03:00", "fuso": "America/Sao_Paulo"}, "arte": "out/post/feed.png", "elementos_ia": []}
    if brief_extra:
        brief.update(brief_extra)
    row = {"max_hashtags": 2, "alt_max": 100, "max_chars": 2200}
    if fmt_extra:
        row.update(fmt_extra)
    formats = {"ig-feed-4x5": row}
    approvals = {"schema_version": 2, "by": "Ana", "at": NOW, "piece": "post-dia-x", "brand_id": "leo-lions", "format": "ig-feed-4x5", "brief": {"sha256": "0" * 64, "by": "Ana", "at": NOW}, "artifacts": [{"path": "out/post/feed.png", "sha256": sha, "bytes": len(ARTE)}], "hash": {"algoritmo": "sha256", "valor": sha, "arquivo": "out/post/feed.png", "bytes": len(ARTE)}}
    return brief, brand, formats, approvals
def _manifesto(root):
    return json.loads((root / "entrega" / "manifesto.json").read_text(encoding="utf-8"))
def test_hashtags_minimas(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    b, brand, fmts, ap = _base(tmp_path, hashtags=["a", "b"], fmt_extra={"min_hashtags": 3, "max_hashtags": 5})
    with pytest.raises(ForjaError) as e:
        delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
    assert (e.value.code, e.value.details["campo"]) == ("BRIEF_INCOMPLETE", "hashtags")
    b["hashtags"] = ["a", "b", "c"]
    delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
    b["hashtags"] = ["a", "b", "c", "d", "e", "f"]
    with pytest.raises(ForjaError) as e2:
        delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
    assert (e2.value.code, e2.value.details["campo"]) == ("BRIEF_INCOMPLETE", "hashtags")
    b["hashtags"] = ["a", "b"]
    sem_min = {"ig-feed-4x5": {"max_hashtags": 5, "alt_max": 100, "max_chars": 2200}}
    delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=sem_min, approvals=ap)
def test_cta_obrigatorio(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    b, brand, fmts, ap = _base(tmp_path, fmt_extra={"cta_obrigatorio": True})
    with pytest.raises(ForjaError) as e:
        delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
    assert (e.value.code, e.value.details["campo"]) == ("BRIEF_INCOMPLETE", "cta")
    b["cta"] = {"texto": "Inscreva-se", "destino": ""}
    with pytest.raises(ForjaError) as e2:
        delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
    assert (e2.value.code, e2.value.details["campo"]) == ("BRIEF_INCOMPLETE", "cta")
    b["cta"] = {"texto": "Inscreva-se", "destino": "https://exemplo.org/a"}
    delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
    assert _manifesto(tmp_path)["cta"] == {"texto": "Inscreva-se", "destino": "https://exemplo.org/a"}
    b2, br2, f2, a2 = _base(tmp_path)
    delivery.build_package(tmp_path, brief=b2, brand_root=br2, formats=f2, approvals=a2)
def test_cta_destino_url(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    for bad in ("http://exemplo.org", "exemplo.org", "javascript:alert(1)"):
        b, brand, fmts, ap = _base(tmp_path, brief_extra={"cta": {"texto": "T", "destino": bad}})
        with pytest.raises(ForjaError) as e:
            delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
        assert (e.value.code, e.value.details["campo"]) == ("CONFIG_INVALID", "cta.destino")
    b, brand, fmts, ap = _base(tmp_path, brief_extra={"cta": {"texto": "T", "destino": "https://exemplo.org/a"}})
    delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
def test_legenda_limite(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    b, brand, fmts, ap = _base(tmp_path, fmt_extra={"max_chars": 50}, brief_extra={"legenda": "x" * 51})
    with pytest.raises(ForjaError) as e:
        delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
    assert (e.value.code, e.value.details["campo"]) == ("BRIEF_INCOMPLETE", "legenda")
    b["legenda"] = "x" * 50
    delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
def test_alt_condicional(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    b, brand, fmts, ap = _base(tmp_path, alt="", fmt_extra={"alt_obrigatorio": True})
    with pytest.raises(ForjaError) as e:
        delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
    assert (e.value.code, e.value.details["campo"]) == ("BRIEF_INCOMPLETE", "alt")
    b["alt"] = "   "
    with pytest.raises(ForjaError) as e2:
        delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
    assert (e2.value.code, e2.value.details["campo"]) == ("BRIEF_INCOMPLETE", "alt")
    b["alt"] = "Voluntários plantam árvores"
    delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
    b2, br2, f2, a2 = _base(tmp_path, alt="", fmt_extra={"alt_obrigatorio": False})
    delivery.build_package(tmp_path, brief=b2, brand_root=br2, formats=f2, approvals=a2)
    b3, br3, f3, a3 = _base(tmp_path, alt="")
    delivery.build_package(tmp_path, brief=b3, brand_root=br3, formats=f3, approvals=a3)
def test_consentimento(tmp_path):
    from forja import delivery
    from forja.errors import ForjaError
    assert ForjaError is not None and delivery is not None
    for extra in ({"pessoas": True}, {"pessoas": True, "consent": False}):
        b, brand, fmts, ap = _base(tmp_path, brief_extra=extra)
        delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
        assert _manifesto(tmp_path)["avisos"] == ["BRIEF_CONSENT_PENDING"]
    b, brand, fmts, ap = _base(tmp_path, brief_extra={"pessoas": True, "consent": True, "responsavel": "Ana Lima"})
    delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
    m = _manifesto(tmp_path)
    assert m["avisos"] == [] and m["consentimento"] == {"responsavel": "Ana Lima"}
    b, brand, fmts, ap = _base(tmp_path)
    delivery.build_package(tmp_path, brief=b, brand_root=brand, formats=fmts, approvals=ap)
    m = _manifesto(tmp_path)
    assert m["avisos"] == [] and "consentimento" not in m
