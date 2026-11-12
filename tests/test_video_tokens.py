"""Contrato do wrapper tokens->Remotion (T-VID-TOKENS-01, plano:2638).

Wrapper fino (plano:2606) sobre forja.brand_tokens.py (plano:1449): le
design-tokens.json e mapeia para brand (primary, ink, paper, accent, font,
safe_margin), saida de build_props (plano:1574: fonte unica da marca).
CLI fixada: --tokens <arquivo> (relativo ao CWD) -> objeto brand em stdout,
exit 0; uso/entrada invalida -> exit 2, stdout vazio (1=gate, 2=uso/entrada).
# LACUNA: o plano nao diz o token de `primary` nem se aceita override de cor
#   valido; e nao decide se todo ".." e recusado ou so o que escapa da raiz.
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "od" / "tokens_to_remotion.py"
TOKENS = [
    {"name": "--bg", "value": "#ffffff", "type": "color", "layer": "base"},
    {"name": "--fg", "value": "#0d2240", "type": "color", "layer": "base"},
    {"name": "--accent", "value": "#00338d", "type": "color", "layer": "base"},
    {"name": "--font-display", "value": "Roboto", "type": "font", "layer": "base"},
    {"name": "--safe", "value": "48px", "type": "dimension", "layer": "base"},
]


def _write(path, tokens=TOKENS):
    path.write_text(json.dumps({"schemaVersion": 1, "format": "od-design-tokens/v1",
                                "tokens": tokens}), encoding="utf-8")


def _run(cwd, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=str(cwd),
                          capture_output=True, text=True, timeout=30)


def _refused(cwd, *args):
    proc = _run(cwd, *args)
    assert (proc.returncode, proc.stdout) == (2, "")
    return proc


def test_happy_path_prints_the_brand_object(tmp_path):
    _write(tmp_path / "design-tokens.json")
    proc = _run(tmp_path, "--tokens", "design-tokens.json")
    assert proc.returncode == 0
    brand = json.loads(proc.stdout)
    assert set(brand) == {"primary", "ink", "paper", "accent", "font", "safe_margin"}
    assert (brand["ink"].lower(), brand["paper"].lower(), brand["accent"].lower()) == (
        "#0d2240", "#ffffff", "#00338d")
    assert (brand["font"], brand["safe_margin"]) == ("Roboto", 48)
    assert re.fullmatch(r"#[0-9A-Fa-f]{6}", brand["primary"])


def test_wrapper_delegates_to_forja_brand_tokens():
    source = SCRIPT.read_text(encoding="utf-8")
    assert re.search(
        r"(?:from\s+forja\.brand_tokens\s+import|from\s+forja\s+import\s+brand_tokens"
        r"|import\s+forja\.brand_tokens)", source)


def test_missing_tokens_argument_is_a_usage_error(tmp_path):
    assert _refused(tmp_path).stderr.strip()


def test_missing_tokens_file_is_an_input_error(tmp_path):
    assert "nao-existe.json" in _refused(tmp_path, "--tokens", "nao-existe.json").stderr


@pytest.mark.parametrize("tokens", [[], {"--accent": "#00338d"}])
def test_empty_or_wrong_tokens_shape_is_refused(tmp_path, tokens):
    _write(tmp_path / "design-tokens.json", tokens=tokens)
    _refused(tmp_path, "--tokens", "design-tokens.json")


def test_truncated_json_is_refused(tmp_path):
    (tmp_path / "design-tokens.json").write_text('{"tokens": [', encoding="utf-8")
    _refused(tmp_path, "--tokens", "design-tokens.json")


def test_loose_hex_on_argv_is_refused(tmp_path):
    _write(tmp_path / "design-tokens.json")
    _refused(tmp_path, "--tokens", "design-tokens.json", "--accent", "#ff0000")


def test_path_with_dotdot_is_refused(tmp_path):
    (tmp_path / "sub").mkdir()
    _write(tmp_path / "design-tokens.json")
    _refused(tmp_path / "sub", "--tokens", "../design-tokens.json")


def test_script_has_no_network_imports():
    source = SCRIPT.read_text(encoding="utf-8")
    assert not re.search(
        r"^\s*(?:import|from)\s+(?:socket|ssl|urllib|http|requests|aiohttp|httpx)\b",
        source, re.MULTILINE)
