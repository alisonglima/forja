"""Contrato T-MCP-01 (plano:2626; lane L-MCP-01 em forja/mcp.py, plano:2594).
8 tools herdadas + 6 novas = 14 (plano:408; total 14 em plano:1840).
Novas tools sao wrappers finos de `forja run --only ... --json` (plano:546).
`project` obrigatorio; retorno = envelope; `isError` se exit != 0 (plano:546).
Sem aprovar/entregar/publicar/abrir navegador; sem --data/--template/--formato (plano:546-557).
`forja_approve` segue por compatibilidade, uso humano apenas (plano:557).
"""
from __future__ import annotations

import io
import json

import pytest

NEW = ("forja_post_plan", "forja_post_render", "forja_post_inspect",
       "forja_lote_validate", "forja_lote_render", "forja_package")
ONLY = {"forja_post_plan": "brief,research,copy,template,compose",
        "forja_post_render": "render", "forja_post_inspect": "lint,inspect",
        "forja_lote_validate": "validate-data", "forja_lote_render": "render-lote",
        "forja_package": "deliver"}
FORCEABLE = {"forja_post_plan", "forja_post_render", "forja_lote_render"}


def _cap(monkeypatch, code=0, text='{"ok": true, "data": {}}'):
    seen = {}

    def _fake(argv, env=None, out=None, err=None):
        seen["argv"] = list(argv)
        if out is not None:
            out.write(text)
        return code

    monkeypatch.setattr("forja.mcp.cli.main", _fake)
    return seen


def _call(name, arguments, rid=1):
    from forja import mcp

    resp = mcp.handle_message(
        {"jsonrpc": "2.0", "id": rid, "method": "tools/call",
         "params": {"name": name, "arguments": arguments}}, env={})
    assert "result" in resp, "tool ausente ou erro de protocolo: %r" % (resp,)
    return resp


def _only_of(argv):
    return argv[argv.index("--only") + 1]


def test_tools_list_has_eight_plus_six():
    from forja import mcp

    names = {t["name"] for t in mcp.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, env={})["result"]["tools"]}
    assert names == {"forja_describe", "forja_providers", "forja_status",
                     "forja_doctor", "forja_init", "forja_run", "forja_qa",
                     "forja_approve"} | set(NEW)


def test_new_tool_schemas_need_only_project_and_force_subset():
    from forja import mcp

    got = {t["name"]: t["inputSchema"] for t in mcp.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, env={})["result"]["tools"]}
    for name in NEW:
        assert got[name]["required"] == ["project"]
        assert "data" not in got[name]["properties"]
        assert "template" not in got[name]["properties"]
        assert "formato" not in got[name]["properties"]
        want = {"project", "force"} if name in FORCEABLE else {"project"}
        assert set(got[name]["properties"]) == want


@pytest.mark.parametrize("name", NEW)
def test_new_tool_wraps_run_only_with_envelope(tmp_path, monkeypatch, name):
    seen = _cap(monkeypatch)
    result = _call(name, {"project": str(tmp_path)})["result"]
    assert result["isError"] is False
    assert _only_of(seen["argv"]) == ONLY[name]
    assert "--json" in seen["argv"] and "run" in seen["argv"]
    assert ("--dry-run" in seen["argv"]) == (name == "forja_post_plan")
    assert json.loads(result["content"][0]["text"]) == {"ok": True, "data": {}}


@pytest.mark.parametrize("name", sorted(FORCEABLE))
def test_force_maps_to_flag(tmp_path, monkeypatch, name):
    seen = _cap(monkeypatch)
    _call(name, {"project": str(tmp_path)})
    assert "--force" not in seen["argv"]
    _call(name, {"project": str(tmp_path), "force": True})
    assert seen["argv"][-1] == "--force"


@pytest.mark.parametrize("name", NEW)
def test_missing_project_is_error(name):
    assert _call(name, {})["result"]["isError"] is True


@pytest.mark.parametrize("name", NEW)
def test_project_must_be_string(name, tmp_path):
    assert _call(name, {"project": 123})["result"]["isError"] is True
    # LACUNA: contrato nao decide `force` nao-booleano; so fixa `force` -> `--force`.


def test_non_object_arguments_is_error():
    from forja import mcp

    response = mcp.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "forja_package", "arguments": ["x"]}}, env={})
    assert response["result"]["isError"] is True


def test_failed_exit_sets_is_error_with_envelope_text(tmp_path, monkeypatch):
    _cap(monkeypatch, code=1, text='{"ok": false, "error": {"code": "GATE_FAILED"}}')
    result = _call("forja_post_inspect", {"project": str(tmp_path)})["result"]
    assert result["isError"] is True
    assert json.loads(result["content"][0]["text"])["ok"] is False


def test_new_tools_never_approve_deliver_confirm_nor_slides(tmp_path, monkeypatch):
    seen = _cap(monkeypatch)
    for name in NEW:
        _call(name, {"project": str(tmp_path)})
        for banned in ("--confirm", "--by", "--hash", "approve", "deliver"):
            assert banned not in seen["argv"]
    # LACUNA: contrato nao fixa campos de `data`; so o --only e o envelope/isError.
    from forja import mcp

    names = {t["name"] for t in mcp.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, env={})["result"]["tools"]}
    assert not {n for n in names if "slides" in n}


def test_hostile_path_passthrough_and_truncated_json(tmp_path, monkeypatch):
    seen = _cap(monkeypatch)
    evil = str(tmp_path) + "/../fora"
    assert _call("forja_lote_validate", {"project": evil})["result"]["isError"] is False
    assert seen["argv"][2] == evil
    from forja import mcp

    stdout = io.StringIO()
    assert mcp.serve(io.StringIO("{truncado\n"), stdout, io.StringIO(), env={}) == 0
    assert json.loads(stdout.getvalue())["error"]["code"] == -32700
