from __future__ import annotations

import io
import json
import sys

from forja import cli, mcp


def _init_project(path):
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(
        ["--json", "init", str(path), "--no-require-approvals"],
        env={},
        out=out,
        err=err,
    )
    assert code == 0, err.getvalue()
    return path


def _call(name, arguments, request_id=1):
    response = mcp.handle_message(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
        env={},
    )
    assert response is not None
    return response


def test_initialize_advertises_tools():
    response = mcp.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        },
        env={},
    )
    assert response["result"]["serverInfo"]["name"] == "forja"
    assert "tools" in response["result"]["capabilities"]


def test_tools_list_has_the_documented_tools():
    response = mcp.handle_message(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, env={}
    )
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert names == {
        "forja_describe",
        "forja_providers",
        "forja_status",
        "forja_doctor",
        "forja_init",
        "forja_run",
        "forja_qa",
        "forja_approve",
    }


def test_status_tool_returns_cli_envelope(tmp_path):
    project = _init_project(tmp_path / "p")
    response = _call("forja_status", {"project": str(project)})
    result = response["result"]
    assert result["isError"] is False
    envelope = json.loads(result["content"][0]["text"])
    assert envelope["project"] == "p"
    assert envelope["steps"]


def test_unknown_tool_is_a_protocol_error():
    response = _call("nao_existe", {})
    assert response["error"]["code"] == -32602


def test_serve_reads_newline_delimited_messages():
    stdin = io.StringIO(
        "\n".join(
            [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {},
                    }
                ),
                json.dumps(
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
                ),
            ]
        )
        + "\n"
    )
    stdout, stderr = io.StringIO(), io.StringIO()
    assert mcp.serve(stdin, stdout, stderr, env={}) == 0
    lines = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert [item["id"] for item in lines] == [1, 2]
    assert lines[1]["result"]["tools"]


def test_cli_mcp_serve_uses_stdin(monkeypatch):
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 7, "method": "ping", "params": {}})
            + "\n"
        ),
    )
    out, err = io.StringIO(), io.StringIO()
    assert cli.main(["mcp", "serve"], env={}, out=out, err=err) == 0
    response = json.loads(out.getvalue())
    assert response == {"jsonrpc": "2.0", "id": 7, "result": {}}
