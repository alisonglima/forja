"""Contrato de `forja.brand_manifest` (N-13; plano:767,805,837,1997).

Congela `load_manifest(path) -> dict`, `validate_manifest(data, root,
variants=None) -> list[dict]` (item com `level`/`code`/`msg`) e
`brand_hash(root) -> str`, que inclui `variants.json`/`voice.json` quando
existem (plano:767). O manifest declara `variants`, `default_variant` e
`variants_file` (plano:1967); a paleta guarda so neutros (plano:1993); o
cross-check confere lista/default, paleta e ausencia de hex duplicado
(plano:1997). Em `provisorio`, arquivo ausente e pendencia; em `final`, erro
(plano:730).
# LACUNA: o plano nao fixa nomes de chaves de fontes/licenca, logos, voz/
# palavras proibidas nem aprovador; o teste cobre cross-check/hash sem inventar.
# LACUNA: nao ha codigo de issue fixado para manifest/default/paleta invalidos
# (so BRAND_VARIANT_REQUIRED no brief/deck, plano:481,1970): exige-se level=error.
# LACUNA: nao ha excecao fixada para JSON truncado/raiz nao-dict: aceita ValueError ou ForjaError (falha fechada).
"""
import json
import shutil
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "brands" / "leo-lions"
FILES = ("manifest.json", "variants.json", "voice.json")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _copy_brand(tmp_path, names=FILES):
    target = tmp_path / "brand"
    target.mkdir()
    for name in names:
        shutil.copy2(BRAND / name, target / name)
    return target


def _errors(issues):
    assert isinstance(issues, list)
    for issue in issues:
        assert {"level", "code", "msg"} <= set(issue)
        assert isinstance(issue["code"], str) and issue["code"]
        assert isinstance(issue["msg"], str) and issue["msg"]
    return [issue for issue in issues if issue.get("level") == "error"]


def test_load_manifest_returns_the_json_object(tmp_path):
    from forja import brand_manifest
    data = {"brand_id": "leo-lions", "variants": ["lions"]}
    _write(tmp_path / "manifest.json", data)
    assert brand_manifest.load_manifest(tmp_path / "manifest.json") == data


@pytest.mark.parametrize("raw", ['{"brand_id": "leo-lions"', "[]", ""])
def test_load_manifest_rejects_bad_json_or_root(tmp_path, raw):
    from forja import brand_manifest
    from forja.errors import ForjaError
    path = tmp_path / "manifest.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises((ValueError, ForjaError)):
        brand_manifest.load_manifest(path)


def test_load_manifest_rejects_absent_file(tmp_path):
    from forja import brand_manifest
    from forja.errors import ForjaError
    with pytest.raises((FileNotFoundError, ForjaError)):
        brand_manifest.load_manifest(tmp_path / "nao-existe.json")


def test_validate_manifest_accepts_real_provisional_brand():
    from forja import brand_manifest
    data = brand_manifest.load_manifest(BRAND / "manifest.json")
    assert _errors(brand_manifest.validate_manifest(data, BRAND)) == []


def test_validate_manifest_accepts_preloaded_variants():
    from forja import brand_manifest
    data = brand_manifest.load_manifest(BRAND / "manifest.json")
    variants = _read(BRAND / "variants.json")
    assert _errors(brand_manifest.validate_manifest(data, BRAND, variants=variants)) == []


@pytest.mark.parametrize("case", ["empty", "status", "sem_variants", "hex", "duplicado"])
def test_validate_manifest_rejects_bad_data(tmp_path, case):
    from forja import brand_manifest
    data = {} if case == "empty" else brand_manifest.load_manifest(BRAND / "manifest.json")
    if case == "status":
        data["status"] = "rascunho"
    elif case == "sem_variants":
        data.pop("variants")
    elif case == "hex":
        data["palette"] = ["#FFFFFF", "#12345G"]
    elif case == "duplicado":
        data["palette"] = ["#FFFFFF", "#FFFFFF"]
    assert _errors(brand_manifest.validate_manifest(data, tmp_path))


@pytest.mark.parametrize("case", ["default", "lista", "escape", "absoluto"])
def test_validate_manifest_cross_checks_variants(tmp_path, case):
    from forja import brand_manifest
    data = brand_manifest.load_manifest(BRAND / "manifest.json")
    root = BRAND
    if case == "default":
        data["default_variant"] = "inexistente"
    elif case == "lista":
        data["variants"] = ["lions", "leo-lion"]
    else:
        data["variants_file"] = "../fora.json" if case == "escape" else "/etc/passwd"
        root = tmp_path
    assert _errors(brand_manifest.validate_manifest(data, root))


@pytest.mark.parametrize("status,has_error", [("provisorio", False), ("final", True)])
def test_validate_manifest_treats_missing_voice_by_status(tmp_path, status, has_error):
    from forja import brand_manifest
    root = _copy_brand(tmp_path, names=("manifest.json", "variants.json"))
    data = brand_manifest.load_manifest(root / "manifest.json")
    data["status"] = status
    assert bool(_errors(brand_manifest.validate_manifest(data, root))) is has_error


def test_brand_hash_is_64_hex_and_stable(tmp_path):
    from forja import brand_manifest
    root = _copy_brand(tmp_path)
    first = brand_manifest.brand_hash(root)
    assert len(first) == 64 and int(first, 16) >= 0
    assert brand_manifest.brand_hash(root) == first


@pytest.mark.parametrize("name", FILES)
def test_brand_hash_changes_with_each_covered_file(tmp_path, name):
    from forja import brand_manifest
    root = _copy_brand(tmp_path)
    before = brand_manifest.brand_hash(root)
    data = _read(root / name)
    data["_teste_hash"] = name
    _write(root / name, data)
    assert brand_manifest.brand_hash(root) != before


def test_brand_hash_ignores_absent_optional_files(tmp_path):
    from forja import brand_manifest
    value = brand_manifest.brand_hash(_copy_brand(tmp_path, names=("manifest.json",)))
    assert len(value) == 64 and int(value, 16) >= 0
