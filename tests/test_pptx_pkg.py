"""Contrato de empacotamento do python-pptx (T-PPTX-PKG-01).

Congela o elo L-PPTX-PKG-01: ``pyproject.toml`` declara
``python-pptx>=1.0,<2`` em ``[project].dependencies`` e nao repete a
declaracao em nenhuma tabela de requisitos (plano:1899, plano:1913,
plano:1923). O teste le o arquivo, nao instala nem importa python-pptx.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ">=1.0,<2"


def _load(text):
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.9/3.10: tomli vem com o pytest
        import tomli as tomllib
    return tomllib.loads(text)


def _requirements(data):
    project = data.get("project", {})
    groups = {
        "build": data.get("build-system", {}).get("requires", []),
        "runtime": project.get("dependencies", []),
    }
    for name, reqs in project.get("optional-dependencies", {}).items():
        groups["extra:" + name] = reqs
    return groups


def _pptx(data):
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name

    found = {}
    for where, reqs in _requirements(data).items():
        matches = [r for r in reqs if canonicalize_name(Requirement(r).name) == "python-pptx"]
        if matches:
            found[where] = matches
    return found


def _pyproject():
    return _load((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_python_pptx_is_a_single_runtime_dependency():
    found = _pptx(_pyproject())
    assert "runtime" in found, "python-pptx ausente de [project].dependencies"
    assert len(found["runtime"]) == 1
    assert "build" not in found


def test_python_pptx_specifier_is_at_least_1_0_and_below_2():
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet

    runtime = _pptx(_pyproject()).get("runtime", [])
    assert len(runtime) == 1
    # LACUNA: o plano nao decide ordem/espacos/1.0.0; compara-se o SpecifierSet.
    assert Requirement(runtime[0]).specifier == SpecifierSet(EXPECTED)


def test_python_pptx_is_not_declared_twice_anywhere():
    # LACUNA: "sem duplicar" nao define escopo; conta-se build+runtime+extras.
    found = _pptx(_pyproject())
    assert sum(len(matches) for matches in found.values()) == 1


def test_optional_only_declaration_is_not_a_runtime_dependency():
    data = _load('[project]\noptional-dependencies = { test = ["python-pptx>=1.0,<2"] }\n')
    found = _pptx(data)
    assert "runtime" not in found
    assert found == {"extra:test": ["python-pptx>=1.0,<2"]}


def test_missing_dependencies_array_yields_no_declaration():
    assert _pptx(_load("[project]\nname = 'forja'\n")) == {}


def test_duplicate_declaration_with_other_spelling_is_detected():
    text = '[project]\ndependencies = ["python-pptx>=1.0,<2", "Python_PPTX<2,>=1.0"]\n'
    assert len(_pptx(_load(text))["runtime"]) == 2


def test_commented_out_requirement_is_ignored():
    text = '[project]\ndependencies = [\n  # "python-pptx>=1.0,<2",\n  "pyyaml>=6",\n]\n'
    assert _pptx(_load(text)) == {}


def test_truncated_pyproject_is_rejected():
    with pytest.raises(ValueError):
        _load('[project]\ndependencies = ["python-pptx>=1.0,<2"')
