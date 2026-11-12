"""Contrato de `brands/leo-lions/assets-index.json` (congela L-ASSETS-INDEX-01).

Cabeça `forja-brand-assets/v1`, `brand: leo-lions`, `root_env` +
default `.work/fontes/lions`, de `SHA256SUMS.txt` (plano:1762-1763);
só relativo + sha256, nunca o binário (plano:1757). Cada ativo declara
`variant`/`variants[]` com licença (plano:1759,230); 7 emblemas por
variante (plano:1778-1786), 4 decks `pptx` c/ `template_id`, 3 extras
`optional` (plano:1786); fotos só em `photos-index.json` (plano:1759,1788).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "brands" / "leo-lions" / "assets-index.json"
HEX64 = re.compile(r"[0-9a-f]{64}")
VARIANTS = {"lions", "leo", "leo-lion"}
EMBLEMS = {
    "leo-emblema-2c": ("leo", "109141433__Logo_rgb_Leo_2C.png"),
    "leo-emblema-alpha-gray": ("leo", "109141431__Logo_rgb_Leo_2C_Alpha_GrayText.png"),
    "leo-emblema-omega-white": ("leo", "109141435__Logo_rgb_Leo_2C_Omega_WhiteText.png"),
    "leo-lion-assinatura-3c-blue": ("leo-lion", "109141436__Logo_rgb_Leo-Lion_3C_BlueText.png"),
    "leo-lion-assinatura-1c-white": ("leo-lion", "109141428__Logo_rgb_Leo-Lion_1C_White.png"),
    "lions-emblema-2c": ("lions", "76039637__lionlogo_2c.jpg"),
    "lions-assinatura-2c": ("lions", "90875984__LCI_primary_sig_2color.png"),
}
DECKS = {"lions-oficial-2022", "mission-brief-2026", "service-journey-2026", "new-club-development-2026"}
BASE_PATH = "box/C-apresentacoes/LI_BrandResources_Template_PPT_13.3x7.5_Presentation_00a.pptx"
BASE_SHA256 = "4a5b521de577453a7e50065a2a1fc5d658879ccde37267a1e8a56ad84f6f9d24"


def _load():
    assert INDEX.is_file(), "assets-index.json ausente"
    try:
        data = json.loads(INDEX.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        assert False, "assets-index.json com JSON truncado/invalido"
    assert isinstance(data, dict), "raiz do indice deve ser objeto"
    return data


def test_top_level_schema_and_roots():
    data = _load()
    assert data["schema"] == "forja-brand-assets/v1"
    assert data["brand"] == "leo-lions"
    assert data["root_env"] == "FORJA_BRAND_SOURCES"
    assert data["root_default"] == ".work/fontes/lions"
    assert data["generated_from"] == "SHA256SUMS.txt"
    # LACUNA: exemplo fixa "2026-11-11" sem dizer se é exata; cobra-se o formato.
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["checked_at"])


def test_assets_list_has_at_least_emblems_and_decks():
    assets = _load()["assets"]
    assert isinstance(assets, list) and len(assets) >= 11


def test_asset_ids_are_unique():
    assets = _load()["assets"]
    assert len({a["id"] for a in assets}) == len(assets)


def test_each_asset_has_required_fields_with_exact_types():
    for a in _load()["assets"]:
        assert isinstance(a["id"], str) and a["id"]
        assert isinstance(a["kind"], str) and a["kind"]
        assert isinstance(a["path"], str) and a["path"]
        assert isinstance(a["sha256"], str) and HEX64.fullmatch(a["sha256"])
        # LACUNA: exemplo traz "bytes": 0 p/ logo mas texto manda calcular;
        # cobra-se tipo int exato e limite >= 0.
        assert type(a["bytes"]) is int and a["bytes"] >= 0
        assert isinstance(a["license"], str) and a["license"].strip()


def test_each_asset_declares_a_known_variant():
    for a in _load()["assets"]:
        single = isinstance(a.get("variant"), str) and a["variant"] in VARIANTS
        multi = isinstance(a.get("variants"), list) and a["variants"] != []
        multi = multi and all(v in VARIANTS for v in a["variants"])
        assert single or multi


def test_asset_paths_are_relative_and_stay_inside_root():
    for a in _load()["assets"]:
        assert "\\" not in a["path"]
        assert not re.match(r"^[A-Za-z]:|^[\\/]", a["path"])
        assert ".." not in Path(a["path"]).parts


def test_index_has_no_embedded_binary():
    raw = INDEX.read_text(encoding="utf-8")
    # LACUNA: sem teto oficial; 1MB é tripwire contra binário embutido.
    assert len(raw.encode("utf-8")) < 1_000_000
    for a in json.loads(raw)["assets"]:
        assert not (set(a) & {"data", "blob", "content", "base64"})
        assert "data:" not in a["path"]


def test_photos_library_is_not_duplicated_here():
    for a in _load()["assets"]:
        assert "box-extra" not in a["path"]
        assert a["kind"] != "photo"


def test_seven_emblems_present_with_expected_variant():
    by_id = {a["id"]: a for a in _load()["assets"]}
    assert set(EMBLEMS) <= set(by_id)
    for eid, (want, _) in EMBLEMS.items():
        got = by_id[eid].get("variant")
        assert got == want or want in (by_id[eid].get("variants") or [])


def test_emblem_filenames_match_official_sources():
    by_id = {a["id"]: a for a in _load()["assets"]}
    for eid, (_, fname) in EMBLEMS.items():
        assert Path(by_id[eid]["path"]).name == fname


def test_four_decks_with_template_id_and_variants():
    decks = [a for a in _load()["assets"] if a["kind"] == "pptx"]
    assert len(decks) == 4
    assert {d["template_id"] for d in decks} == DECKS
    for d in decks:
        assert isinstance(d["variants"], list) and d["variants"]
        assert all(v in VARIANTS for v in d["variants"])


def test_three_extra_decks_are_marked_optional():
    decks = [a for a in _load()["assets"] if a["kind"] == "pptx"]
    assert {d["template_id"] for d in decks if d.get("optional") is True} == DECKS - {"lions-oficial-2022"}


def test_base_deck_pins_official_file_hash_and_bytes():
    # LACUNA: exemplo (plano:1764) diz id "pptx-oficial" sem template_id, mas
    # plano:1786 exige template_id nos 4; cobra-se o segundo.
    base = [a for a in _load()["assets"] if a.get("template_id") == "lions-oficial-2022"]
    assert len(base) == 1
    assert base[0]["path"] == BASE_PATH
    assert base[0]["sha256"] == BASE_SHA256
    assert base[0]["bytes"] == 18518334
