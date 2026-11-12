"""Carrega o calendario 2027 e avisa `checked_at` vencido (plano:2603)."""
from __future__ import annotations

import json
from datetime import date, timedelta
from importlib import resources  # nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2 (requires-python >= 3.9)
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


def _as_date(value):
    """Converte data ISO; entrada invalida vira CONFIG_INVALID."""
    if not isinstance(value, str):
        raise _fail("CONFIG_INVALID", f"data invalida: {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _fail("CONFIG_INVALID", f"data invalida: {value}") from exc


def _week(day):
    ano, semana, _ = day.isocalendar()
    return f"{ano}-W{semana:02d}"


def check_cadence(datas, minimo=1, ideal=(2, 3)) -> list:
    """Avisa semanas abaixo do minimo ou do ideal, entre a primeira e a ultima."""
    if not isinstance(minimo, int) or isinstance(minimo, bool) or minimo < 0:
        raise _fail("CONFIG_INVALID", "minimo deve ser inteiro nao negativo")
    if (not isinstance(ideal, (list, tuple)) or len(ideal) != 2
            or any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in ideal)):
        raise _fail("CONFIG_INVALID", "ideal deve ser par de inteiros nao negativos")
    if datas is None:
        return []
    if isinstance(datas, (str, bytes)):
        raise _fail("CONFIG_INVALID", "datas deve ser lista de datas ISO")
    try:
        dias = [_as_date(item) for item in datas]
    except TypeError as exc:
        raise _fail("CONFIG_INVALID", "datas deve ser lista de datas ISO") from exc
    if not dias:
        return []
    semanas = {}
    for dia in dias:
        segunda = dia - timedelta(days=dia.weekday())
        semanas[segunda] = semanas.get(segunda, 0) + 1
    issues = []
    segunda, fim = min(semanas), max(semanas)
    while segunda <= fim:
        total, wid = semanas.get(segunda, 0), _week(segunda)
        if total < minimo:
            issues.append({"id": wid, "level": "warn", "code": "CADENCE_GAP", "count": total,
                           "msg": f"{wid} abaixo do minimo ({total}/{minimo})"})
        elif total < ideal[0]:
            issues.append({"id": wid, "level": "info", "code": "CADENCE_BELOW_IDEAL",
                           "count": total, "msg": f"{wid} abaixo do ideal ({total}/{ideal[0]})"})
        segunda += timedelta(days=7)
    return issues


def weekly_grid(causas, semanas, inicio) -> list:
    """Grade semanal a partir da segunda da semana de `inicio`, em rodizio."""
    if not isinstance(causas, (list, tuple)) or not causas:
        raise _fail("CONFIG_INVALID", "causas deve ser lista nao vazia")
    if any(not isinstance(c, str) or not c.strip() for c in causas):
        raise _fail("CONFIG_INVALID", "causa deve ser texto nao vazio")
    if not isinstance(semanas, int) or isinstance(semanas, bool) or semanas < 1:
        raise _fail("CONFIG_INVALID", "semanas deve ser inteiro positivo")
    segunda = _as_date(inicio)
    segunda -= timedelta(days=segunda.weekday())
    grid = []
    for i in range(semanas):
        dia = segunda + timedelta(weeks=i)
        grid.append({"semana": _week(dia), "segunda": dia.isoformat(),
                     "causa": causas[i % len(causas)]})
    return grid
