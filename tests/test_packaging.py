"""Contrato de empacotamento: descobrir ``forja*`` e levar os JSON de data/schemas.

Congela ``plano:708`` (empacotamento), ``plano:792`` (N-02), ``plano:793``
(N-02b..d) e ``plano:828`` (T-NUC-PKG):
- o wheel sai de ``[tool.setuptools.packages.find] include = ["forja*"]``, nao
  de lista ``packages`` explicita; ``brands/<id>/`` fica fora (dado de projeto);
- ``[tool.setuptools.package-data]`` declara ``*.json`` para ``forja.data`` e
  ``forja.schemas``;
- ``forja/photo``, ``forja/data`` e ``forja/schemas`` sao pacotes (tem
  ``__init__.py``) e a descoberta ``forja*`` cobre os subpacotes.
"""
import fnmatch
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _pyproject():
    return (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def _table(text, name):
    match = re.search(
        r"(?ms)^\s*\[" + re.escape(name) + r"\]\s*(?:#.*)?$(.*?)(?=^\s*\[|\Z)",
        text,
    )
    return match.group(1) if match else ""


def _array(block, key):
    match = re.search(
        r"(?ms)^\s*[\"']?" + re.escape(key) + r"[\"']?\s*=\s*(\[.*?\])", block
    )
    if match is None:
        return None
    body = match.group(1)[1:-1]
    return [item.strip().strip("\"'") for item in body.split(",") if item.strip()]


def test_tool_setuptools_drops_explicit_package_list():
    block = _table(_pyproject(), "tool.setuptools")
    assert re.search(r"(?m)^\s*packages\s*=", block) is None, (
        "a lista explicita de packages deve dar lugar a packages.find"
    )


def test_package_discovery_uses_only_the_forja_namespace():
    block = _table(_pyproject(), "tool.setuptools.packages.find")
    assert block, "falta a tabela [tool.setuptools.packages.find]"
    assert _array(block, "include") == ["forja*"]


@pytest.mark.parametrize("package", ["forja.data", "forja.schemas"])
def test_package_data_ships_json_for_namespace(package):
    block = _table(_pyproject(), "tool.setuptools.package-data")
    assert block, "falta a tabela [tool.setuptools.package-data]"
    assert re.search(
        r"(?m)^\s*[\"']" + re.escape(package) + r"[\"']\s*=", block
    ), f"{package} precisa de chave literal entre aspas (senao vira tabela aninhada)"
    patterns = _array(block, package)
    assert patterns is not None, f"falta a chave {package} em package-data"
    assert "*.json" in patterns


@pytest.mark.parametrize("name", ["photo", "data", "schemas"])
def test_new_package_has_init_file(name):
    init = ROOT / "forja" / name / "__init__.py"
    assert init.is_file(), f"falta {init.relative_to(ROOT)}"


@pytest.mark.parametrize("name", ["photo", "data", "schemas"])
def test_package_discovery_matches_new_package(name):
    block = _table(_pyproject(), "tool.setuptools.packages.find")
    include = _array(block, "include") or []
    assert any(
        fnmatch.fnmatchcase(f"forja.{name}", pattern) for pattern in include
    ), f"include nao cobre forja.{name}"
