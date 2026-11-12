"""Contrato de `forja/brand_tokens.py`: tokens do design system -> `brand` do video.

Congela L-VID-BRAND-01 (plano:2604; cobre T-VID-BRAND-01 em plano:2636): le
`design-tokens.json` e gera `brand` com as chaves `primary`, `ink`, `paper`,
`accent`, `font` e `safe_margin` (plano:1449, plano:1574); valida contraste
4.5:1 e recusa hex solto (plano:1449); a saida alimenta `build_props` de
`forja/render.py` (plano:1449, plano:2462). Decisao Z.1 #21 (plano:2462).
"""
import json

import pytest

# LACUNA: o contrato nomeia o modulo e as chaves, mas nao a funcao; este teste fixa load_brand(caminho, variante).
# LACUNA: o contrato nao fixa os `name` dos tokens; este teste usa os proprios nomes das chaves de brand.
# LACUNA: o contrato diz "contraste 4.5:1" sem par; este teste fixa tinta-sobre-papel (texto normal).
# LACUNA: o contrato nao nomeia codigo de erro; todo recuso aqui aceita qualquer ForjaError, nunca excecao nua.


def _brand_tokens(accent="#00338D", ink="#0D2240", paper="#FFFFFF",
                  primary="#00338D", font="Roboto", safe_margin=48,
                  layer="variant:lions"):
    return [
        {"name": "primary", "value": primary, "type": "color", "layer": layer},
        {"name": "ink", "value": ink, "type": "color", "layer": layer},
        {"name": "paper", "value": paper, "type": "color", "layer": layer},
        {"name": "accent", "value": accent, "type": "color", "layer": layer},
        {"name": "font", "value": font, "type": "font", "layer": layer},
        {"name": "safe_margin", "value": safe_margin, "type": "dimension",
         "layer": layer},
    ]


def _write_tokens(root, tokens, name="design-tokens.json"):
    doc = {"schemaVersion": 1, "format": "od-design-tokens/v1",
           "contract": "TOKEN_SCHEMA", "tokens": tokens}
    path = root / name
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_maps_tokens_to_brand_with_exact_keys(tmp_path):
    from forja import brand_tokens

    path = _write_tokens(tmp_path, _brand_tokens())
    assert brand_tokens.load_brand(path, "lions") == {
        "primary": "#00338D", "ink": "#0D2240", "paper": "#FFFFFF",
        "accent": "#00338D", "font": "Roboto", "safe_margin": 48,
    }


def test_output_is_stable_across_calls(tmp_path):
    from forja import brand_tokens

    path = _write_tokens(tmp_path, _brand_tokens())
    first = brand_tokens.load_brand(path, "lions")
    second = brand_tokens.load_brand(path, "lions")
    assert first == second


def test_leo_variant_selects_leo_accent(tmp_path):
    from forja import brand_tokens

    tokens = _brand_tokens(layer="variant:leo", primary="#55565A",
                           ink="#FFFFFF", paper="#0D2240", accent="#00AB68")
    path = _write_tokens(tmp_path, tokens)
    assert brand_tokens.load_brand(path, "leo")["accent"] == "#00AB68"


def test_ink_paper_below_contrast_floor_is_refused(tmp_path):
    from forja import brand_tokens
    from forja.errors import ForjaError

    path = _write_tokens(tmp_path, _brand_tokens(ink="#B3B2B1"))
    with pytest.raises(ForjaError):
        brand_tokens.load_brand(path, "lions")


def test_loose_hex_is_refused(tmp_path):
    from forja import brand_tokens
    from forja.errors import ForjaError

    for bad in ("#fff", "red"):
        path = _write_tokens(tmp_path, _brand_tokens(accent=bad))
        with pytest.raises(ForjaError):
            brand_tokens.load_brand(path, "lions")


def test_missing_file_is_refused(tmp_path):
    from forja import brand_tokens
    from forja.errors import ForjaError

    with pytest.raises(ForjaError):
        brand_tokens.load_brand(tmp_path / "ausente.json", "lions")


def test_empty_token_list_is_refused(tmp_path):
    from forja import brand_tokens
    from forja.errors import ForjaError

    path = _write_tokens(tmp_path, [])
    with pytest.raises(ForjaError):
        brand_tokens.load_brand(path, "lions")


def test_truncated_json_is_refused(tmp_path):
    from forja import brand_tokens
    from forja.errors import ForjaError

    path = tmp_path / "design-tokens.json"
    path.write_text('{"schemaVersion": 1, "tokens": [', encoding="utf-8")
    with pytest.raises(ForjaError):
        brand_tokens.load_brand(path, "lions")


def test_parent_segment_in_path_is_refused(tmp_path):
    from forja import brand_tokens
    from forja.errors import ForjaError

    real = _write_tokens(tmp_path, _brand_tokens())
    tricky = tmp_path / "sub" / ".." / real.name
    with pytest.raises(ForjaError):
        brand_tokens.load_brand(tricky, "lions")


def test_tokens_with_wrong_type_is_refused(tmp_path):
    from forja import brand_tokens
    from forja.errors import ForjaError

    path = _write_tokens(tmp_path, "--accent")
    with pytest.raises(ForjaError):
        brand_tokens.load_brand(path, "lions")


def test_unknown_variant_is_refused(tmp_path):
    from forja import brand_tokens
    from forja.errors import ForjaError

    path = _write_tokens(tmp_path, _brand_tokens())
    with pytest.raises(ForjaError):
        brand_tokens.load_brand(path, "dragoes")
