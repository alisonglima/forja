"""Contrato T-ASSETS-01 de forja/assets.py (cobre L-ASSETS-01).
Congela plano:62 (lions/leo/leo-lion); plano:217 (variant slug, obrigatorio se >1;
ausente BRAND_VARIANT_REQUIRED exit 2, desconhecido CONFIG_INVALID exit 2; lista de
variants.json); plano:438 (valida arquivo/hash/licenca/origem, copia, grava
work/assets.json; falta de arquivo/manifesto ASSET_MISSING); plano:758 (le so o
canonico); plano:2003 (cada ativo declara variant/variants[]). LACUNAs no fim.
"""
import hashlib
import json
import pytest
def _bytes(root, rel, data):
    p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
def _manifest(root, items):
    b = root / "incoming"; b.mkdir(parents=True, exist_ok=True)
    (b / "manifest.json").write_text(json.dumps({"schema": "incoming/v1", "items": items}), encoding="utf-8")
def _item(arq, sha, n, **kw):
    d = {"id": "capa", "arquivo": arq, "sha256": sha, "bytes": n, "origem": "flow",
         "license": "Lions International; uso autorizado", "variant": "lions"}
    d.update(kw); return d
def _entry(root):
    data = json.loads((root / "work/assets.json").read_text(encoding="utf-8"))
    items = data.get("assets", data.get("items", []))
    return data, next(e for e in items if e.get("id") == "capa")
def test_happy_copies_file_and_lists_asset(tmp_path):
    from forja import assets
    raw = b"capa-bytes"; sha = _bytes(tmp_path, "incoming/capa.png", raw)
    _manifest(tmp_path, [_item("incoming/capa.png", sha, len(raw))])
    out = assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
    data, e = _entry(tmp_path)
    assert out == data and e["sha256"] == sha and e["bytes"] == len(raw)
    assert (tmp_path / "work/assets/capa.png").read_bytes() == raw
def test_happy_accepts_variants_list_form(tmp_path):
    from forja import assets
    raw = b"leo-bytes"; sha = _bytes(tmp_path, "incoming/leo.png", raw)
    it = _item("incoming/leo.png", sha, len(raw)); del it["variant"]; it["variants"] = ["leo"]
    _manifest(tmp_path, [it]); assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
    assert _entry(tmp_path)[1]["sha256"] == sha
def test_missing_manifest_raises_asset_missing(tmp_path):
    from forja import assets
    from forja.errors import ForjaError
    with pytest.raises(ForjaError) as ex:
        assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
    assert (ex.value.code, ex.value.exit_code) == ("ASSET_MISSING", 2)
def test_missing_asset_file_raises_asset_missing(tmp_path):
    from forja import assets
    from forja.errors import ForjaError
    _manifest(tmp_path, [_item("incoming/falta.png", hashlib.sha256(b"x").hexdigest(), 1)])
    with pytest.raises(ForjaError) as ex:
        assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
    assert (ex.value.code, ex.value.exit_code) == ("ASSET_MISSING", 2)
def test_empty_arquivo_raises_asset_missing(tmp_path):
    from forja import assets
    from forja.errors import ForjaError
    _manifest(tmp_path, [_item("", "0" * 64, 0)])
    with pytest.raises(ForjaError) as ex:
        assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
    assert ex.value.code == "ASSET_MISSING"
def test_hash_mismatch_fails_closed(tmp_path):
    from forja import assets
    from forja.errors import ForjaError
    _bytes(tmp_path, "incoming/capa.png", b"real")
    _manifest(tmp_path, [_item("incoming/capa.png", hashlib.sha256(b"outro").hexdigest(), 4)])
    with pytest.raises(ForjaError):
        assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
def test_missing_license_fails_closed(tmp_path):
    from forja import assets
    from forja.errors import ForjaError
    raw = b"sem-licenca"; sha = _bytes(tmp_path, "incoming/capa.png", raw)
    it = _item("incoming/capa.png", sha, len(raw)); del it["license"]
    _manifest(tmp_path, [it])
    with pytest.raises(ForjaError):
        assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
def test_unknown_origem_fails_closed(tmp_path):
    from forja import assets
    from forja.errors import ForjaError
    raw = b"origem-ruim"; sha = _bytes(tmp_path, "incoming/capa.png", raw)
    _manifest(tmp_path, [_item("incoming/capa.png", sha, len(raw), origem="radio")])
    with pytest.raises(ForjaError):
        assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
def test_missing_variant_requires_brand_variant(tmp_path):
    from forja import assets
    from forja.errors import ForjaError
    raw = b"sem-variante"; sha = _bytes(tmp_path, "incoming/capa.png", raw)
    it = _item("incoming/capa.png", sha, len(raw)); del it["variant"]
    _manifest(tmp_path, [it])
    with pytest.raises(ForjaError) as ex:
        assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
    assert (ex.value.code, ex.value.exit_code) == ("BRAND_VARIANT_REQUIRED", 2)
def test_unknown_variant_is_config_invalid(tmp_path):
    from forja import assets
    from forja.errors import ForjaError
    raw = b"variante-orca"; sha = _bytes(tmp_path, "incoming/capa.png", raw)
    _manifest(tmp_path, [_item("incoming/capa.png", sha, len(raw), variant="orca")])
    with pytest.raises(ForjaError) as ex:
        assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
    assert (ex.value.code, ex.value.exit_code) == ("CONFIG_INVALID", 2)
def test_invalid_variant_slug_is_config_invalid(tmp_path):
    from forja import assets
    from forja.errors import ForjaError
    raw = b"slug-ruim"; sha = _bytes(tmp_path, "incoming/capa.png", raw)
    _manifest(tmp_path, [_item("incoming/capa.png", sha, len(raw), variant="Leo!")])
    with pytest.raises(ForjaError) as ex:
        assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
    assert ex.value.code == "CONFIG_INVALID"
def test_single_variant_brand_does_not_require_variant(tmp_path):
    from forja import assets
    raw = b"unica"; sha = _bytes(tmp_path, "incoming/capa.png", raw)
    it = _item("incoming/capa.png", sha, len(raw)); del it["variant"]
    _manifest(tmp_path, [it]); assets.build_assets(tmp_path, ["lions"])
    assert _entry(tmp_path)[1]["sha256"] == sha
def test_path_traversal_never_writes_outside(tmp_path):
    from forja import assets
    _manifest(tmp_path, [_item("../fora.bin", "0" * 64, 1, variant="lions")])
    with pytest.raises(Exception):
        assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
    assert not (tmp_path / "fora.bin").exists()
    assert not (tmp_path / "work/assets/fora.bin").exists()
def test_truncated_manifest_json_fails_closed(tmp_path):
    from forja import assets
    from forja.errors import ForjaError
    b = tmp_path / "incoming"; b.mkdir(parents=True, exist_ok=True)
    (b / "manifest.json").write_text("{quebrado", encoding="utf-8")
    with pytest.raises(ForjaError):
        assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
def test_wrong_type_variant_fails_closed(tmp_path):
    from forja import assets
    raw = b"tipo-errado"; sha = _bytes(tmp_path, "incoming/capa.png", raw)
    _manifest(tmp_path, [_item("incoming/capa.png", sha, len(raw), variant=123)])
    with pytest.raises(Exception):
        assets.build_assets(tmp_path, ["lions", "leo", "leo-lion"])
# LACUNA: codigo de sha divergente nao nomeado em plano:438/476 (ASSET_MISSING x ASSET_HASH_MISMATCH).
# LACUNA: codigo de licenca ausente e origem desconhecida nao nomeado; so "valida" em plano:438.
# LACUNA: chave do conteiner do manifesto (items/assets) e de work/assets.json nao fixada; teste aceita assets|items.
# LACUNA: arquivo relativo a raiz (DESIGN.md:348) assumido; ai-studio x ai_studio diverge (plano:438 x :758).
