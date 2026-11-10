"""Servidor MCP minimo por stdio (JSON-RPC 2.0, uma mensagem por linha).

Nao depende de SDK externo. Cada tool chama a CLI em processo, com `--json`,
e devolve o envelope como texto. Nenhum segredo e logado no stdout.
"""
from __future__ import annotations

import io
import json
import os
from typing import Any

from . import __version__, cli

PROTOCOL_VERSION = "2024-11-05"


def _schema(properties=None, required=None) -> dict:
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


def _string(description):
    return {"type": "string", "description": description}


def _bool(description):
    return {"type": "boolean", "description": description}


TOOLS = [
    {
        "name": "forja_describe",
        "description": "Descreve comandos, workflows, providers, schemas e erros do Forja.",
        "inputSchema": _schema(),
    },
    {
        "name": "forja_providers",
        "description": "Lista providers de TTS registrados e o estado do ambiente.",
        "inputSchema": _schema(),
    },
    {
        "name": "forja_status",
        "description": "Mostra o estado dos passos de um projeto e a proxima acao.",
        "inputSchema": _schema({"project": _string("Diretorio do projeto")}, ["project"]),
    },
    {
        "name": "forja_doctor",
        "description": "Confere pre-requisitos do ambiente sem expor segredos.",
        "inputSchema": _schema({"project": _string("Diretorio do projeto (default: .)")}),
    },
    {
        "name": "forja_init",
        "description": "Cria a estrutura de um projeto e o config.yaml.",
        "inputSchema": _schema(
            {
                "dir": _string("Diretorio do novo projeto"),
                "source": _string("Video de entrada (opcional)"),
                "workflow": {"type": "string", "enum": ["dub", "storyboard"]},
                "force": _bool("Sobrescreve arquivos existentes"),
                "no_require_approvals": _bool("Desliga o gate de aprovacoes humanas"),
            },
            ["dir"],
        ),
    },
    {
        "name": "forja_run",
        "description": "Executa o workflow em ordem, com cache.",
        "inputSchema": _schema(
            {
                "project": _string("Diretorio do projeto"),
                "only": _string("Passos separados por virgula"),
                "force": _bool("Ignora o cache"),
                "dry_run": _bool("Nao executa nem grava"),
                "strict": _bool("Falha se o QA reprovar"),
            },
            ["project"],
        ),
    },
    {
        "name": "forja_qa",
        "description": "Roda o gate de qualidade do resultado.",
        "inputSchema": _schema(
            {"project": _string("Diretorio do projeto"), "strict": _bool("Falha se houver erro")},
            ["project"],
        ),
    },
    {
        "name": "forja_approve",
        "description": "Registra aprovacoes humanas de roteiro, voz, overlays e publicacao.",
        "inputSchema": _schema(
            {
                "project": _string("Diretorio do projeto"),
                "script": _bool("Aprova roteiro/cues"),
                "voice": _bool("Aprova elenco/vozes"),
                "overlays": _bool("Aprova overlays"),
                "publish": _bool("Aprova publicacao"),
                "by": _string("Quem aprovou"),
            },
            ["project"],
        ),
    },
]


def _json_error(request_id, code, message, data=None) -> dict:
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _result(request_id, result) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _run_cli(argv, env) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    try:
        code = cli.main(list(argv), env=env, out=out, err=err)
    except Exception as exc:  # nunca traceback para o cliente MCP
        return 5, "", "forja: erro interno: %s" % exc
    return int(code), out.getvalue().strip(), err.getvalue().strip()


def _tool_text(name: str, args: dict, env) -> tuple[str, bool]:
    if not isinstance(args, dict):
        return "argumentos devem ser um objeto", True
    project = args.get("project")
    if project is not None and not isinstance(project, str):
        return "project deve ser string", True

    if name == "forja_describe":
        argv = ["--json", "describe"]
    elif name == "forja_providers":
        argv = ["--json", "providers"]
    elif name == "forja_status":
        if not project:
            return "project e obrigatorio", True
        argv = ["--json", "--project", project, "status"]
    elif name == "forja_doctor":
        argv = ["--json", "--project", project or ".", "doctor"]
    elif name == "forja_init":
        directory = args.get("dir")
        if not isinstance(directory, str) or not directory:
            return "dir e obrigatorio", True
        argv = ["--json", "init", directory]
        source = args.get("source")
        if source is not None:
            if not isinstance(source, str):
                return "source deve ser string", True
            argv += ["--source", source]
        workflow = args.get("workflow")
        if workflow is not None:
            if workflow not in ("dub", "storyboard"):
                return "workflow deve ser dub ou storyboard", True
            argv += ["--workflow", workflow]
        if args.get("force"):
            argv.append("--force")
        if args.get("no_require_approvals"):
            argv.append("--no-require-approvals")
    elif name == "forja_run":
        if not project:
            return "project e obrigatorio", True
        argv = ["--json", "--project", project, "run"]
        only = args.get("only")
        if only is not None:
            if not isinstance(only, str):
                return "only deve ser string", True
            argv += ["--only", only]
        if args.get("force"):
            argv.append("--force")
        if args.get("dry_run"):
            argv.append("--dry-run")
        if args.get("strict"):
            argv.append("--strict")
    elif name == "forja_qa":
        if not project:
            return "project e obrigatorio", True
        argv = ["--json", "--project", project, "qa"]
        if args.get("strict"):
            argv.append("--strict")
    elif name == "forja_approve":
        if not project:
            return "project e obrigatorio", True
        argv = ["--json", "--project", project, "approve"]
        for flag in ("script", "voice", "overlays", "publish"):
            if args.get(flag):
                argv.append("--" + flag)
        by = args.get("by")
        if by is not None:
            if not isinstance(by, str):
                return "by deve ser string", True
            argv += ["--by", by]
    else:
        return "tool desconhecida: %s" % name, True

    code, stdout, stderr = _run_cli(argv, env)
    text = stdout or stderr or "(sem saida)"
    return text, code != 0


def _known_tool(name) -> bool:
    return any(tool.get("name") == name for tool in TOOLS)


def handle_message(message: Any, env=None) -> dict | None:
    env = os.environ if env is None else env
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _json_error(None, -32600, "Invalid Request")
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return _json_error(request_id, -32602, "Invalid params")

    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "forja", "version": __version__},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return _result(request_id, {})
    if method == "tools/list":
        return _result(request_id, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(name, str):
            return _json_error(request_id, -32602, "name da tool e obrigatorio")
        if not _known_tool(name):
            return _json_error(request_id, -32602, "tool desconhecida: %s" % name)
        text, is_error = _tool_text(name, args, env)
        return _result(
            request_id,
            {"content": [{"type": "text", "text": text}], "isError": bool(is_error)},
        )
    if method == "shutdown":
        return _result(request_id, {})
    return _json_error(request_id, -32601, "Method not found")


def serve(stdin, stdout, stderr, env=None) -> int:
    for raw in stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            response = _json_error(None, -32700, "Parse error")
        else:
            response = handle_message(message, env=env)
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0
