"""Contrato do envelope JSON de status/describe (M1) e --project na proxima acao (L2).

Falha hoje pelo motivo certo: `--json status` devolve o documento cru
(`{"project": ...}`) e `--json describe` devolve o documento cru
(`{"version": ...}`), sem `ok`/`data`/`next_actions`; o comando de `next`
nao inclui `--project` e nao roda fora da raiz.
"""
from __future__ import annotations

import io
import json
import shlex


def _run(cli, argv, env=None):
    out = io.StringIO()
    err = io.StringIO()
    code = cli.main(argv, env={} if env is None else env, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def _run_json(cli, argv, env=None):
    code, out, err = _run(cli, argv, env=env)
    return code, json.loads(out), err


def _init_storyboard(cli, path):
    code, doc, err = _run_json(cli, ["--json", "init", str(path)], env={})
    assert code == 0, err
    return doc


def test_describe_json_usa_envelope():
    from forja import cli

    code, doc, _ = _run_json(cli, ["--json", "describe"], env={})
    assert code == 0
    assert doc["ok"] is True
    assert set(doc) == {"ok", "data", "next_actions", "artifacts", "warnings", "cost"}
    assert set(doc["data"]) == {
        "version",
        "exit_codes",
        "error_codes",
        "commands",
        "workflows",
        "providers",
        "schemas",
        "mcp_tools",
    }


def test_describe_envelope_tem_next_actions_vazio_e_custo_nulo():
    from forja import cli

    _, doc, _ = _run_json(cli, ["--json", "describe"], env={})
    assert doc["next_actions"] == []
    assert doc["artifacts"] == []
    assert doc["warnings"] == []
    assert doc["cost"] is None


def test_describe_data_mantem_conteudo_atual():
    from forja import cli

    _, doc, _ = _run_json(cli, ["--json", "describe"], env={})
    data = doc["data"]
    assert isinstance(data["version"], str) and data["version"]
    names = {command["name"] for command in data["commands"]}
    assert {"init", "describe", "status", "run", "qa"} <= names
    assert {"dub", "storyboard"} <= set(data["workflows"])
    assert isinstance(data["providers"], list)


def test_status_json_usa_envelope(tmp_path):
    from forja import cli

    _init_storyboard(cli, tmp_path / "p")
    code, doc, _ = _run_json(
        cli, ["--json", "--project", str(tmp_path / "p"), "status"], env={}
    )
    assert code == 0
    assert doc["ok"] is True
    assert set(doc) == {"ok", "data", "next_actions", "artifacts", "warnings", "cost"}
    assert {"project", "workflow", "steps", "next"} <= set(doc["data"])
    assert doc["cost"] is None
    assert isinstance(doc["artifacts"], list)
    assert isinstance(doc["warnings"], list)


def test_status_next_actions_espelha_next(tmp_path):
    from forja import cli

    _init_storyboard(cli, tmp_path / "p")
    _, doc, _ = _run_json(
        cli, ["--json", "--project", str(tmp_path / "p"), "status"], env={}
    )
    nxt = doc["data"]["next"]
    assert isinstance(nxt, dict) and nxt["command"].startswith("forja")
    assert doc["next_actions"] == [{"command": nxt["command"], "why": nxt["why"]}]


def test_status_next_command_inclui_project(tmp_path):
    from forja import cli

    root = tmp_path / "p"
    _init_storyboard(cli, root)
    _, doc, _ = _run_json(
        cli, ["--json", "--project", str(root), "status"], env={}
    )
    command = doc["next_actions"][0]["command"]
    parts = shlex.split(command)
    assert parts[0] == "forja"
    assert "--project" in parts
    assert parts[parts.index("--project") + 1] == str(root)
    assert "run" in parts and "--only" in parts


def test_status_next_command_cita_caminho_com_espaco(tmp_path):
    from forja import cli

    root = tmp_path / "x; com espaco"
    _init_storyboard(cli, root)
    _, doc, _ = _run_json(
        cli, ["--json", "--project", str(root), "status"], env={}
    )
    command = doc["next_actions"][0]["command"]
    parts = shlex.split(command)
    assert "--project" in parts
    assert parts[parts.index("--project") + 1] == str(root)
    assert shlex.quote(str(root)) in command


def test_status_next_command_roda_de_outro_cwd(tmp_path, monkeypatch):
    from forja import cli

    root = tmp_path / "p"
    _init_storyboard(cli, root)
    _, doc, _ = _run_json(
        cli, ["--json", "--project", str(root), "status"], env={}
    )
    command = doc["next_actions"][0]["command"]
    parts = shlex.split(command)
    assert parts[0] == "forja"
    argv = ["--json"] + parts[1:]
    other = tmp_path / "outro-cwd"
    other.mkdir()
    monkeypatch.chdir(other)
    code, doc2, _ = _run_json(cli, argv, env={})
    assert code == 0, doc2
    assert doc2["ok"] is True


def test_status_next_command_com_espaco_roda_de_outro_cwd(tmp_path, monkeypatch):
    from forja import cli

    root = tmp_path / "x; com espaco"
    _init_storyboard(cli, root)
    _, doc, _ = _run_json(
        cli, ["--json", "--project", str(root), "status"], env={}
    )
    command = doc["next_actions"][0]["command"]
    argv = ["--json"] + shlex.split(command)[1:]
    other = tmp_path / "outro"
    other.mkdir()
    monkeypatch.chdir(other)
    code, doc2, _ = _run_json(cli, argv, env={})
    assert code == 0, doc2
    assert doc2["ok"] is True


def test_status_tudo_fresh_tem_next_actions_vazio(tmp_path, monkeypatch):
    from forja import cli

    root = tmp_path / "p"
    _init_storyboard(cli, root)
    monkeypatch.setattr(cli, "_workflow_steps", lambda name: [])
    code, doc, _ = _run_json(
        cli, ["--json", "--project", str(root), "status"], env={}
    )
    assert code == 0
    assert doc["ok"] is True
    assert doc["data"]["next"] is None
    assert doc["next_actions"] == []


def test_status_texto_sem_json_nao_muda(tmp_path):
    from forja import cli

    root = tmp_path / "p"
    _init_storyboard(cli, root)
    code, out, _ = _run(cli, ["--project", str(root), "status"], env={})
    assert code == 0
    assert out.strip() and "projeto:" in out and "proximo:" in out
    try:
        parsed = json.loads(out)
    except ValueError:
        parsed = None
    assert not isinstance(parsed, dict) or "ok" not in parsed


def test_describe_texto_sem_json_nao_muda():
    from forja import cli

    code, out, _ = _run(cli, ["describe"], env={})
    assert code == 0
    assert "forja" in out and "comandos:" in out


def test_status_projeto_inexistente_continua_erro_json(tmp_path):
    from forja import cli

    code, doc, _ = _run_json(
        cli,
        ["--json", "--project", str(tmp_path / "nao-existe"), "status"],
        env={},
    )
    assert code == 2 and doc["ok"] is False
    assert doc["error"]["code"] == "CONFIG_INVALID"


def test_mcp_status_devolve_envelope(tmp_path):
    from forja import cli, mcp

    out = io.StringIO()
    err = io.StringIO()
    code = cli.main(
        ["--json", "init", str(tmp_path / "p")], env={}, out=out, err=err
    )
    assert code == 0, err.getvalue()
    response = mcp.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "forja_status", "arguments": {"project": str(tmp_path / "p")}},
        },
        env={},
    )
    assert response["result"]["isError"] is False
    envelope = json.loads(response["result"]["content"][0]["text"])
    assert envelope["ok"] is True
    assert envelope["data"]["project"] == "p"
    assert envelope["data"]["steps"]
    assert envelope["next_actions"] == [envelope["data"]["next"]]


def test_mcp_describe_devolve_envelope():
    from forja import mcp

    response = mcp.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "forja_describe", "arguments": {}},
        },
        env={},
    )
    assert response["result"]["isError"] is False
    envelope = json.loads(response["result"]["content"][0]["text"])
    assert envelope["ok"] is True
    assert "version" in envelope["data"]
    assert envelope["next_actions"] == []
