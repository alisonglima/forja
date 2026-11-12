"""Contrato N-08 (plano:62,217,722,832,1968-1969): `variant` slug `^[a-z0-9-]+$`
com oficiais `lions`/`leo`/`leo-lion`; obrigatorio so se `variants.json` tem >1
(ausente `BRAND_VARIANT_REQUIRED`/exit 2, desconhecido `CONFIG_INVALID`/exit 2,
enforcement do validador N-09, plano:481,2025,833); lista vem de `variants.json`.
Schema: COMPASS 7 chaves, 5 elementos, `itens_obrigatorios`, `dados_nao_inventar`,
`licencas`, `rotulo_ia`, `aprovador`, `fonte_mae`, `pontos_chave`<=3 com fonte,
`cta` unico com destino, `restricoes`, `idioma`, `acessibilidade` (plano:722,2514).
# LACUNA: `mode/persona` uma chave ou duas; nomes dos 5 elementos; `required`
# LACUNA: minimo; `additionalProperties`; `$schema`/draft do schema.
"""
import json
import re
from pathlib import Path

import pytest

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "forja" / "schemas" / "brief.schema.json"
OFFICIAL_VARIANTS = ("lions", "leo", "leo-lion")
SLUG = r"^[a-z0-9-]+$"


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _props(schema):
    assert schema["type"] == "object"
    assert isinstance(schema["properties"], dict)
    return schema["properties"]


def test_schema_file_is_valid_json_object():
    schema = _load_schema()
    assert isinstance(schema, dict)
    assert _props(schema) is not None


def test_happy_path_brief_keys_are_all_described():
    props = _props(_load_schema())
    brief = {
        "variant": "leo",
        "compass": {
            "context": "c", "objective": "o", "people": "p",
            "attitude": "a", "style": "s", "specifications": "spec",
        },
        "itens_obrigatorios": [{"texto": "t", "fonte": "f"}],
        "dados_nao_inventar": ["dado"],
        "licencas": [{"tipo": "foto", "fonte": "b", "licenca": "l", "prova": "p"}],
        "rotulo_ia": {"necessario": True, "texto": "gerado por IA"},
        "aprovador": {"nome": "Ana", "papel": "dona"},
        "fonte_mae": "doc-mae",
        "pontos_chave": [{"texto": "p", "fonte": "f"}],
        "cta": {"texto": "participe", "destino": "https://exemplo.test/cta"},
        "restricoes": ["r"],
        "idioma": "pt-BR",
        "acessibilidade": {"alt": "descricao"},
    }
    assert [k for k in brief if k not in props] == []
    compass_props = props["compass"]["properties"]
    assert [k for k in brief["compass"] if k not in compass_props] == []


def test_variant_pattern_is_exact_slug():
    pattern = _props(_load_schema())["variant"]["pattern"]
    assert pattern == SLUG
    assert all(re.fullmatch(pattern, v) for v in OFFICIAL_VARIANTS)


def test_variant_pattern_rejects_non_slugs():
    pattern = _props(_load_schema())["variant"]["pattern"]
    for bad in ("Lions", "LEO", "leo_lion", "", "leo lion", "../x", "..", "leo!"):
        assert not re.fullmatch(pattern, bad), bad


def test_variant_declared_as_string():
    assert _props(_load_schema())["variant"].get("type") == "string"


def test_variant_not_unconditionally_required():
    # Condicional (>1 variante) decidida pelo validador N-09 (plano:833).
    assert "variant" not in _load_schema().get("required", [])


def test_variant_list_not_hardcoded_in_schema():
    enum = _props(_load_schema())["variant"].get("enum", [])
    assert not any(v in enum for v in OFFICIAL_VARIANTS)


def test_compass_has_seven_keys():
    compass = _props(_load_schema())["compass"]
    assert compass.get("type") == "object"
    keys = set(compass["properties"])
    assert {"context", "objective", "people", "attitude", "style", "specifications"} <= keys
    assert {"mode", "persona"} & keys


def test_pontos_chave_capped_at_three():
    assert _props(_load_schema())["pontos_chave"].get("maxItems") == 3


def test_cta_is_a_single_object():
    assert _props(_load_schema())["cta"].get("type") == "object"


def test_licencas_is_array_of_objects():
    lic = _props(_load_schema())["licencas"]
    assert lic.get("type") == "array" and lic.get("items", {}).get("type") == "object"


def test_truncated_json_fails_closed(tmp_path):
    bad = tmp_path / "brief.schema.json"
    bad.write_text('{"type": "object", "properties": {', encoding="utf-8")
    with pytest.raises(ValueError):
        json.loads(bad.read_text(encoding="utf-8"))
