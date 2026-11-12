"""Contrato de dados de `brands/leo-lions/manifest.json` (T-BRAND-DATA, N-14).

Fontes: plano:838 (variants[]/default_variant; sem paleta de variante duplicada),
plano:1967 (lista literal, default "lions", variants_file "variants.json"),
plano:1970 (status só no manifest) e plano:1977 (paleta do manifest só neutros),
plano:1993 (hex de variante vivem em variants.json) e plano:730 (placeholder
"Leo Clube"/"Lions Clube", provisorio).

# LACUNA: o plano não fixa os nomes das chaves de fontes/licença, logos,
# voz/palavras proibidas nem aprovador; N-13 os valida fora deste contrato.
"""
import json
import re
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "brands" / "leo-lions" / "manifest.json"
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")

# plano:1977 — neutros comuns a todas as variantes.
NEUTRAL_HEX = {"#FFFFFF", "#F4F4F2", "#0D2240", "#55565A", "#B3B2B1"}
# plano:1981-1983 — hex que só podem viver em variants.json.
VARIANT_HEX = {"#00338D", "#EBB700", "#7A2582", "#407CCA", "#00AB68", "#FF5B35"}


def _data():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _hexes(value):
    if isinstance(value, str):
        return HEX.findall(value)
    if isinstance(value, dict):
        return [hex_ for item in value.values() for hex_ in _hexes(item)]
    if isinstance(value, list):
        return [hex_ for item in value for hex_ in _hexes(item)]
    return []


def test_manifest_is_a_json_object():
    assert MANIFEST.is_file()
    assert isinstance(_data(), dict)


def test_manifest_declares_the_three_variants_in_order():
    assert _data()["variants"] == ["lions", "leo", "leo-lion"]


def test_default_variant_is_lions():
    data = _data()
    assert data["default_variant"] == "lions"
    assert data["default_variant"] in data["variants"]


def test_variants_file_is_a_plain_relative_filename():
    variants_file = _data()["variants_file"]
    assert variants_file == "variants.json"
    assert "/" not in variants_file and ".." not in variants_file
    assert not Path(variants_file).is_absolute()


def test_manifest_status_is_provisorio():
    assert _data()["status"] == "provisorio"


def test_manifest_palette_has_only_common_neutrals():
    hexes = {item.upper() for item in _hexes(_data()["palette"])}
    assert hexes
    assert hexes <= NEUTRAL_HEX


def test_manifest_does_not_repeat_variant_palette():
    hexes = {item.upper() for item in _hexes(_data())}
    assert hexes.isdisjoint(VARIANT_HEX)


def test_manifest_carries_placeholder_brand_names():
    text = MANIFEST.read_text(encoding="utf-8")
    assert "Leo Clube" in text
    assert "Lions Clube" in text
