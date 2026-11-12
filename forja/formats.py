from __future__ import annotations

# Matriz de formatos por plataforma (ver DESIGN.md, secao formats.py).
import json
from datetime import date
from pathlib import Path

from .errors import ForjaError

_REQUIRED = (
    "id", "plataforma", "formato", "largura", "altura", "razao", "safe_zone",
    "max_chars", "max_hashtags", "alt_max", "fonte", "fonte_tipo",
    "checked_at", "status", "notas")
_MARGINS = ("top", "bottom", "left", "right")
_SOURCE_TYPES = ("oficial", "parceiro", "plano")
_STATUSES = ("confirmado", "provisorio")
_VERIFICACOES = ("VERIFICADO", "DIVERGENTE", "NAO_VERIFICADA")

def _invalid(msg: str):
    raise ForjaError("CONFIG_INVALID", msg)

def _day(value) -> date:
    return date.fromisoformat(str(value)[:10])

def _read(path=None) -> str:
    try:
        if path is None:
            from importlib.resources import files
            return files("forja.data").joinpath("formats.json").read_text(encoding="utf-8")
        return Path(path).read_text(encoding="utf-8")
    except (OSError, TypeError) as exc:
        _invalid("nao foi possivel ler a matriz de formatos: %s" % exc)

def _validate_row(row, index: int) -> dict:
    where = "formato #%d" % index
    if not isinstance(row, dict):
        _invalid("%s nao e um objeto" % where)
    missing = [f for f in _REQUIRED if f not in row or (
        f in ("fonte", "checked_at") and not row[f])]
    if missing:
        _invalid("%s sem os campos: %s" % (where, ", ".join(missing)))
    safe = row.get("safe_zone")
    if not isinstance(safe, dict) or any(k not in safe for k in _MARGINS):
        _invalid("%s com safe_zone incompleta" % where)
    if row["fonte_tipo"] not in _SOURCE_TYPES:
        _invalid("%s com fonte_tipo invalido: %r" % (where, row["fonte_tipo"]))
    if row["status"] not in _STATUSES:
        _invalid("%s com status invalido: %r" % (where, row["status"]))
    fonte = str(row["fonte"])
    if row["fonte_tipo"] == "oficial" and not fonte.startswith(("http://", "https://")):
        _invalid("%s oficial sem URL http(s): %r" % (where, fonte))
    if row["fonte_tipo"] == "plano" and not fonte.startswith("plano:"):
        _invalid("%s de plano sem fonte 'plano:...': %r" % (where, fonte))
    try:
        _day(row["checked_at"])
    except ValueError:
        _invalid("%s com checked_at invalido: %r" % (where, row["checked_at"]))
    if "verificado_em" in row and row["verificado_em"] != row["checked_at"]:
        _invalid("%s com checked_at != verificado_em" % where)
    fixed = dict(row)
    fixed["safe_zone"] = dict(safe)
    verif = fixed.get("verificacao") or "NAO_VERIFICADA"
    if verif not in _VERIFICACOES:
        _invalid("%s com verificacao invalida: %r" % (where, verif))
    fixed["verificacao"] = verif
    if fixed["fonte_tipo"] == "plano" or verif != "VERIFICADO":
        fixed["status"] = "provisorio"
        fixed["constantes"] = []
    return fixed

def load_formats(path=None) -> dict:
    """Le a matriz empacotada (ou `path`) e valida cada linha."""
    try:
        data = json.loads(_read(path))
    except ValueError as exc:
        _invalid("matriz de formatos com JSON invalido: %s" % exc)
    if not isinstance(data, dict) or not isinstance(data.get("formatos"), list):
        _invalid("matriz de formatos deve ser um objeto com a lista 'formatos'")
    data = dict(data)
    data["formatos"] = [_validate_row(r, i) for i, r in enumerate(data["formatos"])]
    return data

def get(ident: str) -> dict:
    """Devolve a linha do formato `ident` da matriz empacotada."""
    for row in load_formats()["formatos"]:
        if row["id"] == ident:
            return row
    raise ForjaError("FORMAT_UNSUPPORTED", "formato fora da matriz: %r" % ident)

def constantes(ident: str) -> list:
    """Campos que podem bloquear a validacao do formato."""
    return list(get(ident).get("constantes") or [])

def require_verified(ident: str, campo: str) -> list:
    """Issues de `FORMAT_UNVERIFIED` quando o formato/campo nao e verificado."""
    row = get(ident)
    if row.get("verificacao") == "VERIFICADO":
        return []
    return [{"level": "error", "id": ident, "code": "FORMAT_UNVERIFIED",
             "msg": "formato %s: campo %s nao verificado (%s)" % (
                 ident, campo, row.get("verificacao"))}]

def stale_rows(data: dict, on=None, days: int = 90) -> list:
    """Avisos `FORMAT_STALE` para `checked_at` com mais de `days` dias."""
    today = _day(on) if on is not None else date.today()
    issues = []
    for row in (data or {}).get("formatos") or []:
        age = (today - _day(row.get("checked_at"))).days
        if age > days:
            issues.append({
                "level": "warning", "id": row.get("id"), "code": "FORMAT_STALE",
                "msg": "formato %s: checked_at %s tem %d dias (limite %d); "
                       "revise %s" % (row.get("id"), row.get("checked_at"),
                                      age, days, row.get("fonte", ""))})
    return issues

def stale(days: int = 90) -> list:
    """Avisos de validade da matriz empacotada."""
    return stale_rows(load_formats(), days=days)
