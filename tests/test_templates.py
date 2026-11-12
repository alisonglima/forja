"""Contrato T-TEMPLATES-01 de `forja/templates.py` (impl. em L-TEMPLATES-01).
Congela: `verify_template`/`promote_template` com copia p/ `brands/<id>/templates/`
e sha256 no `manifest.json` (plano:430, plano:1377); hash divergente vira
`TEMPLATE_HASH_MISMATCH` exit 1 retryable false + details (plano:477, plano:483,
plano:598); ausente vira `MISSING_PREREQ` (plano:421); promocao grava `variants[]`
e recusa template sem `data-variant`/com hex cru (plano:2622, plano:2048, plano:2027);
sem `design_system_sha256`/`kit_version` (plano:1564).
"""
import hashlib
import json
import pytest
VARIANTS = ["lions", "leo", "leo-lion"]
NOW = "2026-11-11T00:00:00Z"
OK = '<div data-od-card data-variant="lions" style="color:var(--accent)">oi</div>'
NODV = '<div data-od-card style="color:var(--accent)">oi</div>'
def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def _brand(tmp_path):
    return tmp_path / "brands" / "leo-lions"
def _promote(t, src, brand, h, **kw):
    p = dict(approved_by="Ana", od_project="leo-lions/c", od_artifact="a1",
             design_system="user:leo-lions", preset="ig-portrait", now=NOW)
    p.update(kw)
    return t.promote_template(src, brand, "post", approve_hash=h, **p)
def test_promote_happy_copies_file_and_writes_manifest_hash(tmp_path):
    from forja import templates
    src = tmp_path / "od" / "post.html"; _write(src, OK)
    out = _promote(templates, src, _brand(tmp_path), _sha(src))
    dest = _brand(tmp_path) / "templates" / "post.html"
    assert dest.read_bytes() == src.read_bytes()
    man = _brand(tmp_path) / "templates" / "manifest.json"
    entry = json.loads(man.read_text("utf-8"))["templates"]["post"]
    assert entry["sha256"] == _sha(dest) == out["sha256"] == _sha(src)
    assert len(entry["sha256"]) == 64 and entry["file"] == "post.html"
    assert entry["approved_by"] == "Ana" and entry["approved_at"] == NOW
def test_promote_manifest_records_variants_list(tmp_path):
    from forja import templates
    src = tmp_path / "od" / "post.html"; _write(src, OK)
    _promote(templates, src, _brand(tmp_path), _sha(src))
    man = _brand(tmp_path) / "templates" / "manifest.json"
    data = json.loads(man.read_text("utf-8"))
    assert data.get("variants", data["templates"]["post"].get("variants")) == VARIANTS
def test_promote_manifest_has_no_extra_version_keys(tmp_path):
    from forja import templates
    src = tmp_path / "od" / "post.html"; _write(src, OK)
    _promote(templates, src, _brand(tmp_path), _sha(src))
    raw = (_brand(tmp_path) / "templates" / "manifest.json").read_text(encoding="utf-8")
    assert "design_system_sha256" not in raw and "kit_version" not in raw
def test_verify_happy_returns_matching_sha256(tmp_path):
    from forja import templates
    src = tmp_path / "od" / "post.html"; _write(src, OK)
    _promote(templates, src, _brand(tmp_path), _sha(src))
    assert templates.verify_template(_brand(tmp_path), "post")["sha256"] == _sha(src)
def test_verify_diverged_hash_is_template_mismatch(tmp_path):
    from forja import templates
    from forja.errors import ForjaError
    src = tmp_path / "od" / "post.html"; _write(src, OK)
    _promote(templates, src, _brand(tmp_path), _sha(src))
    (_brand(tmp_path) / "templates" / "post.html").write_text(OK + "<!-- x -->", "utf-8")
    with pytest.raises(ForjaError) as exc:
        templates.verify_template(_brand(tmp_path), "post")
    assert exc.value.code == "TEMPLATE_HASH_MISMATCH"
    assert exc.value.exit_code == 1 and exc.value.retryable is False
    assert {"brand", "template", "expected", "actual"} <= set(exc.value.details)
@pytest.mark.parametrize("html", ["", NODV])
def test_promote_refuses_template_without_data_variant(tmp_path, html):
    from forja import templates
    from forja.errors import ForjaError
    src = tmp_path / "od" / "post.html"; _write(src, html)
    # LACUNA: plano exige a recusa mas nao nomeia o codigo deste caso.
    with pytest.raises(ForjaError) as exc:
        _promote(templates, src, _brand(tmp_path), _sha(src))
    assert "data-variant" in str(exc.value)
def test_promote_refuses_template_with_raw_hex(tmp_path):
    from forja import templates
    from forja.errors import ForjaError
    src = tmp_path / "od" / "post.html"; _write(src, OK.replace("var(--accent)", "#00338D"))
    # LACUNA: plano exige a recusa mas nao nomeia o codigo deste caso.
    with pytest.raises(ForjaError):
        _promote(templates, src, _brand(tmp_path), _sha(src))
def test_promote_refuses_wrong_approve_hash(tmp_path):
    from forja import templates
    from forja.errors import ForjaError
    src = tmp_path / "od" / "post.html"; _write(src, OK)
    with pytest.raises(ForjaError) as exc:
        _promote(templates, src, _brand(tmp_path), "0" * 64)
    assert exc.value.code == "TEMPLATE_HASH_MISMATCH"
def test_promote_refuses_path_traversal(tmp_path):
    from forja import templates
    from forja.errors import ForjaError
    src = tmp_path / "od" / "post.html"; _write(src, OK)
    # LACUNA: plano exige recusar destino fora de templates/ sem nomear o codigo.
    with pytest.raises(ForjaError):
        templates.promote_template(src, _brand(tmp_path), "../fora", approve_hash=_sha(src),
            approved_by="Ana", od_project="leo-lions/c", od_artifact="a1",
            design_system="user:leo-lions", preset="ig-portrait", now=NOW)
    assert not (_brand(tmp_path) / "fora.html").exists()
def test_promote_does_not_overwrite_without_force(tmp_path):
    from forja import templates
    from forja.errors import ForjaError
    src = tmp_path / "od" / "post.html"; _write(src, OK)
    _promote(templates, src, _brand(tmp_path), _sha(src))
    src.write_text(OK + "<!-- v2 -->", encoding="utf-8")
    # LACUNA: plano exige --force + novo hash mas nao nomeia o codigo da recusa.
    with pytest.raises(ForjaError):
        _promote(templates, src, _brand(tmp_path), _sha(src))
    out = _promote(templates, src, _brand(tmp_path), _sha(src), force=True)
    assert out["sha256"] == _sha(_brand(tmp_path) / "templates" / "post.html")
def test_verify_missing_template_is_missing_prereq(tmp_path):
    from forja import templates
    from forja.errors import ForjaError
    (_brand(tmp_path) / "templates").mkdir(parents=True)
    with pytest.raises(ForjaError) as exc:
        templates.verify_template(_brand(tmp_path), "post")
    assert exc.value.code == "MISSING_PREREQ"
def test_truncated_manifest_fails_closed(tmp_path):
    from forja import templates
    from forja.errors import ForjaError
    _write(_brand(tmp_path) / "templates" / "post.html", OK)
    _write(_brand(tmp_path) / "templates" / "manifest.json", '{"schema":1,"templates":{')
    # LACUNA: plano nao nomeia o codigo p/ manifesto truncado; exige falhar fechado.
    with pytest.raises(ForjaError):
        templates.verify_template(_brand(tmp_path), "post")
def test_promote_refuses_node_modules_source(tmp_path):
    from forja import templates
    from forja.errors import ForjaError
    src = tmp_path / "od" / "node_modules" / "post.html"; _write(src, OK)
    with pytest.raises(ForjaError):
        _promote(templates, src, _brand(tmp_path), _sha(src))
