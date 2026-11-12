"""Carrega o calendario 2027 e avisa `checked_at` vencido (plano:2603)."""
from __future__ import annotations

import json
from datetime import date
from importlib import resources
from pathlib import Path

from forja.errors import ForjaError

_YEAR = 2027
_PACKAGED = "calendario-2027.json"
_REQUIRED = ("data", "pilar", "fonte", "checked_at")
_DOC_KEYS = ("schema_version", "ano", "datas")


def _fail(code, msg, **details):
    return ForjaError(code, msg, details=details or None)


def _row(row):
    """Valida e copia uma linha; os quatro campos do contrato sao obrigatorios."""
    if not isinstance(row, dict):
        raise _fail("CONFIG_INVALID", "linha do calendario deve ser objeto")
    for key in _REQUIRED:
        value = row.get(key)
        if not isinstance(value, str) or not value.strip():
            raise _fail("CONFIG_INVALID", f"linha sem '{key}'", campo=key)
    return dict(row)


def _iso(value):
    day, sep, month = value.partition("/")
    if sep and len(day) == len(month) == 2 and (day + month).isdigit():
        try:
            return date(_YEAR, int(month), int(day)).isoformat()
        except ValueError:
            pass
    return value


def _normalize(payload, packaged):
    """Valida o documento e normaliza a lista empacotada para o formato publico."""
    if packaged:
        if not isinstance(payload, list):
            raise _fail("CONFIG_INVALID", "calendario empacotado deve ser lista")
        rows, extra = payload, {"schema_version": 1, "ano": _YEAR}
    else:
        if not isinstance(payload, dict):
            raise _fail("CONFIG_INVALID", "calendario deve ser objeto JSON")
        for key in _DOC_KEYS:
            if key not in payload:
                raise _fail("CONFIG_INVALID", f"calendario sem '{key}'", campo=key)
        if not isinstance(payload["datas"], list):
            raise _fail("CONFIG_INVALID", "'datas' deve ser lista")
        rows = payload["datas"]
        extra = {key: payload[key] for key in _DOC_KEYS if key != "datas"}
    datas = []
    for row in rows:
        item = _row(row)
        item["data"] = _iso(item["data"]) if packaged else item["data"]
        datas.append(item)
    return dict(extra, datas=datas)


def _read(path):
    if path is None:
        target = resources.files("forja.data").joinpath(_PACKAGED)
    elif not (target := Path(path)).is_file():
        raise _fail("MISSING_INPUT", f"calendario nao encontrado: {target}", path=str(target))
    try:
        return target, target.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise _fail("MISSING_INPUT", f"calendario ilegivel: {target}", path=str(target)) from exc


def load_calendar(path=None) -> dict:
    """Le o calendario empacotado ou `path` e devolve schema_version/ano/datas."""
    target, text = _read(path)
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise _fail("CONFIG_INVALID", f"calendario invalido: {target}") from exc
    return _normalize(payload, path is None)


def stale_rows(data, on=None, days=90) -> list:
    """Avisos `warning` para `checked_at` com mais de `days` dias."""
    rows = (data or {}).get("datas") or []
    ref = date.fromisoformat(on) if on is not None else date.today()
    issues = []
    for row in rows:
        idade = (ref - date.fromisoformat(row["checked_at"])).days
        if idade > days:
            issues.append({"level": "warning", "id": row.get("data"), "days": idade,
                           "code": "CALENDAR_STALE", "fonte": row.get("fonte"),
                           "msg": f"{row.get('data')} desatualizado ha {idade} dias "
                                  f"(checked_at {row['checked_at']}, limite {days})"})
    return issues
