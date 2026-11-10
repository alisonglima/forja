#!/usr/bin/env python3
"""Confere os prompts (e docs) contra a CLI real: todo `forja <comando> --flag` e `./kit.sh <sub>` citado tem de existir.

Uso: python scripts/check-prompts.py [--expect N] [arquivos...]   (padrao: prompts/*.md)
Saida: lista de problemas; exit 1 se houver algum.
"""
from __future__ import annotations

import io
import json
import re
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Nada disto pode aparecer nos prompts/docs entregues a terceiros (nomes antigos, caminhos e hosts do autor).
# As partes sao montadas em tempo de execucao para que este proprio arquivo, que vai no kit,
# nao carregue os termos que ele proibe (o portao de vazamento varre o texto do pacote).
FORBIDDEN = ("/" + "Users/", "@" + "gmail", "AI" + "za", "sk-")
KIT_SUBCOMMANDS = {"setup", "doctor", "build", "new", "run", "shell", "browser-up", "browser-down", "browser-reset"}
GLOBAL_FLAGS = {"--json", "--project", "-h", "--help"}
GLOBAL_WITH_VALUE = {"--project"}
LINE = re.compile(r"(?:\./kit\.sh\s+run|\.\\kit\.ps1\s+run|\bforja)\s+(.+)")
KIT_LINE = re.compile(r"(?:\./kit\.sh|\.\\kit\.ps1)\s+([a-z][a-z-]*)")


def _describe() -> dict:
    from forja import cli

    out, err = io.StringIO(), io.StringIO()
    cli.main(["--json", "describe"], env={}, out=out, err=err)
    doc = json.loads(out.getvalue())
    return doc.get("data", doc)


def _command_table(doc: dict) -> dict:
    table = {}
    for command in doc["commands"]:
        flags = set()
        for arg in command.get("args", []):
            name = arg if isinstance(arg, str) else arg.get("name", "")
            if name.startswith("-"):
                flags.add(name)
        table[command["name"]] = flags
    return table


def _tokens(rest: str) -> list[str]:
    rest = re.split(r"[`|;&]|\s#", rest)[0]  # corta no fim do trecho de codigo/pipe/comentario
    try:
        return shlex.split(rest)
    except ValueError:
        return rest.split()


def check_text(text: str, table: dict, where: str) -> list[str]:
    problems = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in LINE.finditer(line):
            tokens = _tokens(match.group(1))
            command, i = None, 0
            while i < len(tokens):
                token = tokens[i]
                if token in GLOBAL_WITH_VALUE:
                    i += 2
                    continue
                if token.startswith("-"):
                    if token not in GLOBAL_FLAGS:
                        problems.append(f"{where}:{number}: flag global desconhecida {token!r}")
                    i += 1
                    continue
                command = token
                break
            if command is None or command.startswith(("<", "$", "...", "[")):
                continue
            if command not in table:
                problems.append(f"{where}:{number}: comando inexistente {command!r}")
                continue
            for token in tokens[i + 1 :]:
                if token.startswith("--") and token not in table[command] and token not in GLOBAL_FLAGS:
                    problems.append(f"{where}:{number}: `{command}` nao tem a flag {token!r}")
        for match in KIT_LINE.finditer(line):
            sub = match.group(1)
            if sub not in KIT_SUBCOMMANDS:
                problems.append(f"{where}:{number}: subcomando do kit inexistente {sub!r}")
    return problems


def check_forbidden(text: str, where: str) -> list[str]:
    return [f"{where}: termo proibido {word!r}" for word in FORBIDDEN if word in text]


def main(argv: list[str]) -> int:
    expect = None
    if argv[:1] == ["--expect"]:
        expect, argv = int(argv[1]), argv[2:]
    files = [Path(a) for a in argv] or sorted((ROOT / "prompts").glob("*.md"))
    table = _command_table(_describe())
    problems = []
    if expect is not None and len(files) != expect:
        problems.append(f"esperava {expect} arquivo(s), achei {len(files)}")
    for path in files:
        text = path.read_text(encoding="utf-8")
        problems += check_text(text, table, path.name)
        problems += check_forbidden(text, path.name)
    for problem in problems:
        print(problem)
    print(f"{len(files)} arquivo(s) verificado(s), {len(problems)} problema(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
