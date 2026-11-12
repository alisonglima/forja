"""Validador standalone do brief: variante da marca e forma minima.

A lista fechada de variantes vem do proprio `data` (campo `variants`, lido de
`variants.json`); este modulo nunca preenche `variant` com `default_variant`.
Devolve issues `{level, path, code, msg}` e nao grava nem altera o brief.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from .errors import ForjaError

_VARIANT_SLUG = re.compile(r"[a-z0-9-]+")


def _issue(level: str, path: str, code: str, msg: str) -> dict:
    return {"level": level, "path": path, "code": code, "msg": msg}


def _variant_ids(data: dict) -> tuple[list | None, dict | None]:
    """Le `data["variants"]` (lista ou mapa, como no `variants.json`)."""
    raw = data.get("variants")
    if isinstance(raw, dict):
        ids = list(raw)
    elif isinstance(raw, list):
        ids = raw
    else:
        return None, _issue(
            "error", "variants", "BRIEF_SCHEMA",
            "brief.variants deve ser lista ou mapa de variantes",
        )
    if not ids:
        return None, _issue(
            "error", "variants", "BRIEF_SCHEMA",
            "brief.variants nao pode ficar vazio",
        )
    bad = [v for v in ids if not isinstance(v, str) or not _VARIANT_SLUG.fullmatch(v)]
    if bad:
        return None, _issue(
            "error", "variants", "BRIEF_SCHEMA",
            "brief.variants tem id invalido: %s" % ", ".join(map(str, bad)),
        )
    return ids, None


def validate_brief(data) -> list:
    """Valida o brief e devolve issues; nao preenche nenhum campo."""
    if not isinstance(data, dict):
        raise ForjaError("CONFIG_INVALID", "brief deve ser um objeto")
    issues = []
    ids, variant_issue = _variant_ids(data)
    if variant_issue is not None:
        issues.append(variant_issue)
    if "variant" not in data:
        if ids is not None and len(ids) > 1:
            issues.append(_issue(
                "error", "variant", "BRAND_VARIANT_REQUIRED",
                "declare `variant`; a marca tem mais de uma variante",
            ))
        return issues
    variant = data["variant"]
    if not isinstance(variant, str) or not _VARIANT_SLUG.fullmatch(variant):
        issues.append(_issue(
            "error", "variant", "CONFIG_INVALID",
            "brief.variant deve ser slug de letras minusculas, digitos e hifen",
        ))
    elif ids is not None and variant not in ids:
        issues.append(_issue(
            "error", "variant", "CONFIG_INVALID",
            "brief.variant desconhecida: %s" % variant,
        ))
    return issues


def validate_brief_file(path) -> list:
    """Carrega um brief YAML/JSON e valida; arquivo ausente ou ilegivel falha."""
    alvo = Path(path)
    if not alvo.is_file():
        raise ForjaError("MISSING_INPUT", "brief nao encontrado: %s" % alvo)
    try:
        data = yaml.safe_load(alvo.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ForjaError(
            "CONFIG_INVALID", "brief ilegivel: %s" % exc,
            hint="corrija o YAML/JSON do brief e tente de novo",
        ) from exc
    return validate_brief(data)
