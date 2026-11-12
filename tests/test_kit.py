"""Contrato de `forja/kit.py` (wrapper do kit; congela L-KIT-01). Plano §8+§6.V:
- plano:738: argv sem shell `npx --yes @feimacode/open-design-agent-kit@0.4.0
  check <arq> --fail-on error --json` (`export` p/ render); versão fixa, LOCAL;
  `run=` injetável; sem Chrome (saída gravada embutida neste arquivo).
- plano:738: parse do ÚLTIMO JSON (tolera banner npx); erro vira issue/ForjaError
  (`GATE_FAILED` design; `MISSING_PREREQ` sem npx/kit; `PROVIDER_ERROR` sem JSON);
  preserva rule/file/line/msg. plano:769: `export(..., variant=None)`, `check(
  target, *, variant=None, ...)`; ausente só ok sem variantes declaradas.
- plano:62/217: `lions`/`leo`/`leo-lion`; slug; desconhecida → `CONFIG_INVALID`.
"""
from __future__ import annotations

import json
import subprocess

import pytest

KIT = "@feimacode/open-design-agent-kit@0.4.0"
CLEAN = json.dumps({"ok": True, "errors": []})
ERRORS = json.dumps({"ok": False, "errors": [
    {"rule": "contrast", "file": "post.html", "line": 12,
     "message": "contraste 2.1:1 abaixo de 4.5:1"},
    {"rule": "safe-area", "file": "post.html", "line": 30,
     "message": "texto fora da area segura"},
]})


def _page(tmp_path, variant=None):
    attr = f' data-variant="{variant}"' if variant else ""
    target = tmp_path / "post.html"
    target.write_text(f"<html{attr}><body>peca</body></html>", encoding="utf-8")
    return str(target)


def _run(stdout="", *, raises=None, returncode=0):
    calls = []
    def run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        if raises is not None:
            raise raises
        return subprocess.CompletedProcess(cmd, returncode, stdout, "")
    return run, calls


# LACUNA: chaves do dict de check()/export(), params extras de require_check/
# export (preset/formato/saída) e expressão do modo LOCAL não congelados; fonte
# da lista de variantes (variants.json via cwd/brand_root), "marca declara >1 +
# variant ausente", tipo errado em check_issues() e exit!=0 ficam p/ outra lane.

def test_check_monta_argv_pinado_sem_shell(tmp_path):
    from forja import kit
    target = _page(tmp_path)
    run, calls = _run(CLEAN)
    kit.check(target, run=run)
    cmd = calls[0][0]
    assert isinstance(cmd, list) and cmd[:3] == ["npx", "--yes", KIT]
    assert {"check", target, "--fail-on", "error", "--json"} <= set(cmd)
    assert calls[0][1].get("shell", False) is False

def test_check_tolera_banner_do_npx(tmp_path):
    from forja import kit
    target = _page(tmp_path)
    run, _ = _run("npm notice: nova versao disponivel\n" + CLEAN)
    assert isinstance(kit.check(target, run=run), dict)

def test_check_issues_preserva_rule_file_line_msg():
    from forja import kit
    issues = kit.check_issues(json.loads(ERRORS))
    assert len(issues) == 2
    got = [(i["code"], i["file"], i["line"], i["level"]) for i in issues]
    assert got[0] == ("contrast", "post.html", 12, "error")
    assert "contraste" in issues[0]["msg"] and "area segura" in issues[1]["msg"]

def test_require_check_reprova_erro_de_design(tmp_path):
    from forja import kit
    from forja.errors import ForjaError
    target = _page(tmp_path)
    run, _ = _run(ERRORS)
    with pytest.raises(ForjaError) as excinfo:
        kit.require_check(target, run=run)
    assert excinfo.value.code == "GATE_FAILED"

def test_check_sem_npx_e_missing_prereq(tmp_path):
    from forja import kit
    from forja.errors import ForjaError
    run, _ = _run(raises=FileNotFoundError("npx"))
    with pytest.raises(ForjaError) as excinfo:
        kit.check(_page(tmp_path), run=run)
    assert excinfo.value.code == "MISSING_PREREQ"

def test_check_saida_nao_json_e_provider_error(tmp_path):
    from forja import kit
    from forja.errors import ForjaError
    run, _ = _run("ERRO: kit quebrou\nsem json")
    with pytest.raises(ForjaError) as excinfo:
        kit.check(_page(tmp_path), run=run)
    assert excinfo.value.code == "PROVIDER_ERROR"

def test_check_stdout_vazio_e_provider_error(tmp_path):
    from forja import kit
    from forja.errors import ForjaError
    run, _ = _run("")
    with pytest.raises(ForjaError) as excinfo:
        kit.check(_page(tmp_path), run=run)
    assert excinfo.value.code == "PROVIDER_ERROR"

def test_check_json_truncado_e_provider_error(tmp_path):
    from forja import kit
    from forja.errors import ForjaError
    run, _ = _run('{"ok": false, "errors": [{"rule": "cont')
    with pytest.raises(ForjaError) as excinfo:
        kit.check(_page(tmp_path), run=run)
    assert excinfo.value.code == "PROVIDER_ERROR"

def test_check_aceita_variante_conhecida(tmp_path):
    from forja import kit
    target = _page(tmp_path, variant="leo")
    run, _ = _run(CLEAN)
    assert isinstance(kit.check(target, variant="leo", run=run), dict)

def test_check_rejeita_variante_desconhecida(tmp_path):
    from forja import kit
    from forja.errors import ForjaError
    run, _ = _run(CLEAN)
    with pytest.raises(ForjaError) as excinfo:
        kit.check(_page(tmp_path), variant="rosa-inexistente", run=run)
    assert excinfo.value.code == "CONFIG_INVALID"

def test_check_sem_variante_ok_sem_marca(tmp_path):
    from forja import kit
    run, _ = _run(CLEAN)
    assert isinstance(kit.check(_page(tmp_path), run=run), dict)

def test_export_monta_argv_pinado_sem_shell(tmp_path):
    from forja import kit
    target = _page(tmp_path, variant="lions")
    run, calls = _run("work/render/post.png\n")
    assert isinstance(kit.export(target, variant="lions", run=run), dict)
    cmd = calls[0][0]
    assert isinstance(cmd, list) and cmd[:3] == ["npx", "--yes", KIT]
    assert "export" in cmd and target in cmd
    assert calls[0][1].get("shell", False) is False

def test_export_sem_npx_e_missing_prereq(tmp_path):
    from forja import kit
    from forja.errors import ForjaError
    run, _ = _run(raises=FileNotFoundError("npx"))
    with pytest.raises(ForjaError) as excinfo:
        kit.export(_page(tmp_path), run=run)
    assert excinfo.value.code == "MISSING_PREREQ"
