"""Contrato de `remotion-template/src/BrandTheme.jsx` (L-VID-THEME-01).

O plano fixa que o tema faz o merge do `brand` que chega por props no Remotion
e que as chaves sao `primary`, `ink`, `paper`, `accent`, `font`, `safe_margin`
(plano:1574, plano:2609, plano:2642; DESIGN.md:47-48; Overlay.jsx:3-10).
`Root.jsx:42` passa `brand: {}`: vazio/ausente cai nos defaults e chave
presente no `brand` vence. A API minima congelada aqui e `DEFAULT_BRAND` +
`mergeBrand(brand = {})`.
"""
# LACUNA: o plano nao nomeia o export nem a assinatura; fixei os dois nomes acima.
# LACUNA: o plano nao decide tipo invalido de `brand` nem chaves desconhecidas.
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "remotion-template" / "src" / "BrandTheme.jsx"
EXPECTED = {
    "primary": "#C24B2A",
    "ink": "#1A1714",
    "paper": "#F6F1E8",
    "accent": "#C24B2A",
    "font": "Liberation Sans",
    "safe_margin": 48,
}

_HARNESS = """\
const m = await import("./BrandTheme.mjs");
const fn = typeof m.mergeBrand === "function" ? m.mergeBrand : null;
const before = m.DEFAULT_BRAND ?? null;
const snapshot = before ? JSON.parse(JSON.stringify(before)) : null;
const empty = fn ? fn({}) : null;
const absent = fn ? fn() : null;
const partial = fn ? fn({ accent: "#0057B8", safe_margin: 64 }) : null;
process.stdout.write(JSON.stringify({
  exports: Object.keys(m).sort(),
  defaults: snapshot,
  defaults_after: before,
  empty,
  absent,
  partial,
  fresh: Boolean(fn) && empty !== before,
}));
"""


def _report(tmp_path):
    node = shutil.which("node")
    assert node, "node ausente: nao da para avaliar BrandTheme.jsx"
    assert THEME.is_file(), f"arquivo ausente: {THEME}"
    (tmp_path / "BrandTheme.mjs").write_text(THEME.read_text(encoding="utf-8"), encoding="utf-8")
    harness = tmp_path / "harness.mjs"
    harness.write_text(_HARNESS, encoding="utf-8")
    proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=20)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_exports_default_brand_and_merge_brand(tmp_path):
    exports = _report(tmp_path)["exports"]
    assert {"DEFAULT_BRAND", "mergeBrand"} <= set(exports)


def test_default_brand_is_the_documented_six_key_theme(tmp_path):
    assert _report(tmp_path)["defaults"] == EXPECTED


def test_empty_brand_falls_back_to_the_defaults(tmp_path):
    assert _report(tmp_path)["empty"] == EXPECTED


def test_absent_brand_falls_back_to_the_defaults(tmp_path):
    assert _report(tmp_path)["absent"] == EXPECTED


def test_brand_overrides_only_the_keys_it_supplies(tmp_path):
    assert _report(tmp_path)["partial"] == {**EXPECTED, "accent": "#0057B8", "safe_margin": 64}


def test_merge_returns_a_new_object_without_mutating_the_defaults(tmp_path):
    report = _report(tmp_path)
    assert report["fresh"] is True
    assert report["defaults_after"] == EXPECTED
