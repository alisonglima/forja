"""Conteudo do workflow post: pesquisa e copy (L-POST-CONTENT-01).

`run_research` valida o rascunho do agente em `work/research.json` e recusa
pesquisa sem fonte; `run_copy` mede o copy contra a matriz de formatos e grava
`work/copy.json` (plano:2579,420).
"""
from __future__ import annotations

import json
from pathlib import Path

from forja import formats
from forja.errors import ForjaError

DEFAULT_FORMAT = "ig-feed-quadrado"
BRIEF_FIELDS = ("objective", "audience", "tone")
SOURCE_FIELDS = ("url", "titulo", "data", "trecho")


def _fail(code, msg, **details):
    return ForjaError(code, msg, details=details or None)


def _load(path: Path, label: str) -> dict:
    if not path.is_file():
        raise _fail("MISSING_INPUT", "%s ausente: %s" % (label, path),
                    path=str(path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _fail("CONFIG_INVALID", "%s ilegivel: %s" % (label, exc),
                    path=str(path)) from exc
    if not isinstance(data, dict):
        raise _fail("CONFIG_INVALID", "%s deve ser um objeto JSON" % label,
                    path=str(path))
    return data


def _brief(ctx) -> dict:
    data = _load(Path(ctx.work) / "brief.json", "brief")
    empty = [key for key in BRIEF_FIELDS
             if not isinstance(data.get(key), str) or not data[key].strip()]
    if empty:
        raise _fail("BRIEF_INCOMPLETE", "brief sem: %s" % ", ".join(empty),
                    campos=empty)
    return data


def _fontes(ctx) -> list:
    data = _load(Path(ctx.work) / "research.json", "research")
    fontes = data.get("fontes")
    if not isinstance(fontes, list) or not fontes:
        raise _fail("MISSING_INPUT",
                    "research sem fontes: cite a origem de cada afirmacao",
                    path=str(Path(ctx.work) / "research.json"))
    for index, fonte in enumerate(fontes):
        if not isinstance(fonte, dict):
            raise _fail("GATE_FAILED", "fonte #%d deve ser objeto" % index,
                        fonte=index)
        missing = [key for key in SOURCE_FIELDS
                   if not isinstance(fonte.get(key), str) or not fonte[key].strip()]
        if missing:
            raise _fail("GATE_FAILED",
                        "fonte #%d sem: %s" % (index, ", ".join(missing)),
                        fonte=index, campos=missing)
        if not fonte["url"].startswith(("http://", "https://")):
            raise _fail("GATE_FAILED", "fonte #%d sem URL http(s)" % index,
                        fonte=index)
    return fontes


def run_research(ctx) -> dict:
    """Valida o research escrito pelo agente; fonte ausente e erro."""
    _brief(ctx)
    fontes = _fontes(ctx)
    return {"ok": True, "fontes": len(fontes)}


def _draft(brief: dict, fontes: list) -> dict:
    """Rascunho deterministico quando o agente nao gravou `copy.json`."""
    titulo = brief["objective"].strip()
    corpo = fontes[0]["trecho"].strip()
    return {"titulo": titulo, "corpo": corpo, "cta": "Saiba mais",
            "legenda": corpo, "hashtags": [], "alt": titulo}


def _text(copy: dict, key: str) -> str:
    value = copy.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _fail("GATE_FAILED", "copy.%s vazio ou ausente" % key, campo=key)
    return value


def _hashtags(copy: dict) -> list:
    tags = copy.get("hashtags")
    if not isinstance(tags, list) or any(
            not isinstance(tag, str) or not tag.strip() for tag in tags):
        raise _fail("GATE_FAILED", "copy.hashtags deve ser lista de textos",
                    campo="hashtags")
    return tags


def _format_id(ctx, brief: dict) -> str:
    ident = ctx.cfg.get("format") or brief.get("format") or DEFAULT_FORMAT
    return ident if isinstance(ident, str) and ident.strip() else DEFAULT_FORMAT


def _measure(copy: dict, row: dict) -> dict:
    """Aplica os limites de legenda/hashtags/alt da linha de formato."""
    limits = {"max_chars": int(row["max_chars"]),
              "max_hashtags": int(row["max_hashtags"]),
              "alt_max": int(row["alt_max"])}
    legenda = _text(copy, "legenda")
    tags = _hashtags(copy)
    alt = _text(copy, "alt")
    if len(legenda) > limits["max_chars"]:
        raise _fail("GATE_FAILED",
                    "legenda com %d caracteres (limite %d)"
                    % (len(legenda), limits["max_chars"]),
                    campo="legenda", atual=len(legenda),
                    limite=limits["max_chars"])
    if len(tags) > limits["max_hashtags"]:
        raise _fail("GATE_FAILED",
                    "hashtags com %d itens (limite %d)"
                    % (len(tags), limits["max_hashtags"]),
                    campo="hashtags", atual=len(tags),
                    limite=limits["max_hashtags"])
    if len(alt) > limits["alt_max"]:
        raise _fail("GATE_FAILED",
                    "alt com %d caracteres (limite %d)"
                    % (len(alt), limits["alt_max"]),
                    campo="alt", atual=len(alt), limite=limits["alt_max"])
    return limits

def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def run_copy(ctx) -> dict:
    """Mede o copy contra o formato e grava `work/copy.json`."""
    brief = _brief(ctx)
    fontes = _fontes(ctx)
    path = Path(ctx.work) / "copy.json"
    copy = _load(path, "copy") if path.is_file() else _draft(brief, fontes)
    for key in ("titulo", "corpo", "cta"):
        _text(copy, key)
    ident = _format_id(ctx, brief)
    limits = _measure(copy, formats.get(ident))
    _write(path, copy)
    return {"ok": True, "format": ident, "limites": limits}
