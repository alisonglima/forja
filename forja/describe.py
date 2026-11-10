from __future__ import annotations

import copy
import os

from . import config, registry
from .errors import ERROR_CODES

# Tabela dos exit codes da CLI (0 ok ... 5 erro interno).
_EXIT_CODES = {
    0: "ok",
    1: "gate reprovado (check/qa com erro)",
    2: "uso ou configuracao invalida",
    3: "falha externa possivelmente repetivel (rede, cota, 5xx)",
    4: "pre-requisito ausente (ffmpeg, chave, modelo, navegador)",
    5: "erro interno (bug)",
}


def _arg(name, required=False, help_text=""):
    return {"name": name, "required": bool(required), "help": help_text}


# Comandos documentados da CLI v2. `args` descreve apenas os argumentos
# especificos; --json e --project sao globais.
_COMMANDS = [
    {
        "name": "init",
        "summary": "Cria a estrutura de um projeto e o config.yaml.",
        "args": [
            _arg("dir", True, "diretorio do projeto"),
            _arg("--source", False, "video de entrada; sem ele, cria um projeto do workflow storyboard"),
            _arg("--workflow", False, "dub ou storyboard (default: dub com --source, storyboard sem)"),
            _arg("--force", False, "sobrescreve arquivos existentes"),
        ],
    },
    {
        "name": "describe",
        "summary": "Descreve comandos, workflows, provedores, erros e schemas.",
        "args": [],
    },
    {
        "name": "status",
        "summary": "Mostra o estado dos passos e a proxima acao.",
        "args": [],
    },
    {
        "name": "doctor",
        "summary": "Confere os pre-requisitos do ambiente sem expor segredos.",
        "args": [],
    },
    {
        "name": "run",
        "summary": "Executa o workflow em ordem, com cache.",
        "args": [
            _arg("--only", False, "nomes de passos separados por virgula"),
            _arg("--force", False, "ignora o cache"),
            _arg("--dry-run", False, "nao executa nem grava"),
            _arg("--strict", False, "falha se o gate de QA reprovar"),
        ],
    },
    {
        "name": "transcribe",
        "summary": "Transcreve o audio original do clipe.",
        "args": [],
    },
    {
        "name": "frames",
        "summary": "Extrai quadros do clipe para analise.",
        "args": [_arg("--every", False, "intervalo entre quadros em segundos")],
    },
    {
        "name": "check",
        "summary": "Valida as cues e a configuracao antes de gerar vozes.",
        "args": [],
    },
    {
        "name": "voices",
        "summary": "Sintetiza as vozes das cues usando o cache.",
        "args": [
            _arg("--only", False, "ids de cues separados por virgula"),
            _arg("--force", False, "ignora o cache"),
        ],
    },
    {
        "name": "schedule",
        "summary": "Planeja a linha do tempo das falas.",
        "args": [],
    },
    {
        "name": "mix",
        "summary": "Monta a mixagem final com voz e audio original.",
        "args": [],
    },
    {
        "name": "render",
        "summary": "Renderiza o video com as legendas embutidas.",
        "args": [],
    },
    {
        "name": "qa",
        "summary": "Roda o gate de qualidade do resultado.",
        "args": [_arg("--strict", False, "falha se houver erro")],
    },
    {
        "name": "providers",
        "summary": "Lista provedores registrados e o estado do ambiente.",
        "args": [],
    },
]

_CUES_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "t0", "t1", "text"],
        "additionalProperties": True,
        "properties": {
            "id": {"type": "string"},
            "speaker": {"type": "string"},
            "role": {"type": "string", "enum": ["narrator", "speech"]},
            "t0": {"type": "number"},
            "t1": {"type": "number"},
            "lead": {"type": "number"},
            "text": {"type": "string"},
            "source_text": {"type": "string"},
            "voice": {"type": "string"},
            "style": {"type": "string"},
        },
    },
}


def _field(workflow, name, default=None):
    if isinstance(workflow, dict):
        return workflow.get(name, default)
    return getattr(workflow, name, default)


def _step_entry(step):
    return {
        "name": _field(step, "name", ""),
        "doc": _field(step, "doc", ""),
        "needs": list(_field(step, "needs", []) or []),
    }


def _workflow_entry(workflow):
    factory = _field(workflow, "steps_factory")
    if callable(factory):
        steps = list(factory())
    else:
        steps = list(_field(workflow, "steps", []) or [])
    return {
        "summary": _field(workflow, "summary", ""),
        "steps": [_step_entry(step) for step in steps],
        "files": copy.deepcopy(_field(workflow, "files", {}) or {}),
    }


# Provedores embutidos: existem sem registro/entry point e aparecem em `providers`.
_BUILTIN_PROVIDERS = (
    {
        "kind": "tts",
        "name": "files",
        "requires_env": (),
        "network": False,
        "note": "voce gera os WAVs em voices/<id>.wav (padrao)",
    },
    {
        "kind": "tts",
        "name": "mock",
        "requires_env": (),
        "network": False,
        "note": "tom sintetico para testes",
    },
    {
        "kind": "tts",
        "name": "gemini",
        "requires_env": ("GEMINI_API_KEY",),
        "network": True,
        "note": "API opcional do Google",
    },
)


def builtin_providers(env=None) -> list[dict]:
    env = os.environ if env is None else env
    items = []
    for provider in _BUILTIN_PROVIDERS:
        requires = tuple(provider["requires_env"])
        items.append(
            {
                "kind": provider["kind"],
                "name": provider["name"],
                "requires_env": requires,
                "env_ok": all(bool((env.get(name) or "").strip()) for name in requires),
                "network": provider["network"],
                "note": provider["note"],
            }
        )
    return items


def describe(workflows: dict, version: str) -> dict:
    """Documento unico que descreve a plataforma para agentes e humanos."""
    return {
        "version": version,
        "exit_codes": dict(_EXIT_CODES),
        "error_codes": copy.deepcopy(ERROR_CODES),
        "commands": copy.deepcopy(_COMMANDS),
        "workflows": {
            name: _workflow_entry(workflow) for name, workflow in workflows.items()
        },
        "providers": builtin_providers() + registry.available(),
        "schemas": {
            "config": copy.deepcopy(config.DEFAULTS),
            "cues": copy.deepcopy(_CUES_SCHEMA),
        },
    }
