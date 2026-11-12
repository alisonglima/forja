"""Contrato de `forja.brief_validate` (N-09, `L-T-BVAL-01`).
- `validate_brief(data)`/`validate_brief_file(path)` -> `list[dict]` (plano:764).
- Issue `{level, path, code, msg}`; nunca preenche campo (plano:722).
- `variant` slug `^[a-z0-9-]+$`, obrigatório se a marca declara >1 (plano:217).
- Ausente -> `BRAND_VARIANT_REQUIRED`; desconhecido -> `CONFIG_INVALID` (plano:217).
- Lista fechada de `variants.json` (`lions`, `leo`, `leo-lion`); `default_variant`
  nunca preenche em silêncio (plano:1967 item 1); `BRIEF_*`/hash fora do contrato.
"""
import json

import pytest


# `data` carrega `variants` (de `variants.json`): a assinatura (plano:764) não tem
# outro canal; a lista vem do arquivo, nunca do código (plano:217).
def _brief(**over):
    data = {"brand": "leo-lions", "variants": ["lions", "leo", "leo-lion"], "variant": "lions"}
    data.update(over)
    return data

@pytest.mark.parametrize("variant", ["lions", "leo", "leo-lion"])
def test_known_variant_has_no_variant_issue(variant):
    from forja import brief_validate
    issues = brief_validate.validate_brief(_brief(variant=variant))
    assert [i for i in issues if i["code"] in ("BRAND_VARIANT_REQUIRED", "CONFIG_INVALID")] == []

def test_missing_variant_reports_brand_variant_required():
    from forja import brief_validate
    data = _brief()
    del data["variant"]
    issues = brief_validate.validate_brief(data)
    matching = [i for i in issues if i["code"] == "BRAND_VARIANT_REQUIRED"]
    assert len(matching) == 1 and matching[0]["level"] == "error"

def test_unknown_variant_reports_config_invalid():
    from forja import brief_validate
    issues = brief_validate.validate_brief(_brief(variant="tigers"))
    matching = [i for i in issues if i["code"] == "CONFIG_INVALID"]
    assert len(matching) == 1 and matching[0]["level"] == "error"

@pytest.mark.parametrize("variant", ["LIONS", "lions!", "sao paulo", "leo_lion"])
def test_malformed_variant_slug_reports_config_invalid(variant):
    # `leo_lion` é a armadilha real: chave de `tokens-submarcas.json` usa `_`,
    # mas o id oficial é `leo-lion` (plano:1967).
    from forja import brief_validate
    issues = brief_validate.validate_brief(_brief(variant=variant))
    matching = [i for i in issues if i["code"] == "CONFIG_INVALID"]
    assert len(matching) == 1 and matching[0]["level"] == "error"

def test_single_variant_brand_does_not_require_variant():
    from forja import brief_validate
    data = _brief(variants=["lions"])
    del data["variant"]
    issues = brief_validate.validate_brief(data)
    assert [i for i in issues if i["code"] == "BRAND_VARIANT_REQUIRED"] == []

def test_default_variant_never_fills_missing_variant():
    from forja import brief_validate
    data = _brief(default_variant="lions")
    del data["variant"]
    assert "BRAND_VARIANT_REQUIRED" in [i["code"] for i in brief_validate.validate_brief(data)]

def test_issues_carry_level_path_code_msg():
    from forja import brief_validate
    data = _brief()
    del data["variant"]
    issues = brief_validate.validate_brief(data)
    assert issues != []
    assert all({"level", "path", "code", "msg"} <= set(i) for i in issues)

def test_validate_brief_never_fills_fields_itself():
    from forja import brief_validate
    data = _brief()
    del data["variant"]
    snapshot = dict(data)
    brief_validate.validate_brief(data)
    assert data == snapshot

def test_empty_dict_fails_closed():
    # LACUNA: sem marca o contrato não fixa o código (plano:217); vale não aprovar.
    from forja import brief_validate
    assert brief_validate.validate_brief({}) != []

def test_non_dict_input_fails_closed():
    # LACUNA: tipo errado sem comportamento fixado; vale raise ou issues não-vazias.
    from forja import brief_validate
    try:
        issues = brief_validate.validate_brief(["nao-um-dict"])
    except Exception:
        return
    assert issues != []

def test_validate_brief_file_matches_validate_brief(tmp_path):
    # LACUNA: só `path` é fixo (plano:764); JSON aqui também é YAML legível.
    from forja import brief_validate
    data = _brief()
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert brief_validate.validate_brief_file(path) == brief_validate.validate_brief(data)

def test_validate_brief_file_missing_path_raises(tmp_path):
    # LACUNA: arquivo ausente sem comportamento fixado; nunca aprovar com [].
    from forja import brief_validate
    with pytest.raises(Exception):
        brief_validate.validate_brief_file(tmp_path / "ausente.json")

@pytest.mark.parametrize("raw", ['{"brand": "leo-lions", "variant":', '["leo-lions"]'])
def test_validate_brief_file_hostile_content_fails_closed(tmp_path, raw):
    # LACUNA: JSON truncado/tipo errado sem comportamento fixado; fail-closed.
    from forja import brief_validate
    path = tmp_path / "brief.json"
    path.write_text(raw, encoding="utf-8")
    try:
        issues = brief_validate.validate_brief_file(path)
    except Exception:
        return
    assert issues != []

def test_validate_brief_file_dotdot_path_resolves_inside_project(tmp_path):
    from forja import brief_validate
    data = _brief()
    (tmp_path / "brief.json").write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "sub").mkdir()
    tricky = tmp_path / "sub" / ".." / "brief.json"
    assert brief_validate.validate_brief_file(tricky) == brief_validate.validate_brief(data)
