"""Medicao e checagens geometricas de pecas de QA visual.

Le dimensoes/sha256 de PNG sem depender de metadados externos e valida
zona segura e estouro de caixas contra o canvas esperado.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from forja.errors import ForjaError

# Margem segura padrao nos canvases de 1080 px (plano §4.6.8).
SAFE_MARGIN = 48

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_IHDR = b"IHDR"


def _issue(level: str, cid, code: str, msg: str) -> dict:
    return {"level": level, "id": cid, "code": code, "msg": msg}


def measure(path):
    """Devolve width/height/bytes/sha256 do PNG, ou None se ilegivel."""
    try:
        raw = Path(path).read_bytes()
    except (OSError, ValueError, TypeError):
        return None
    if len(raw) < 24 or raw[:8] != _PNG_SIGNATURE:
        return None
    length = int.from_bytes(raw[8:12], "big")
    if raw[12:16] != _IHDR or length != 13:
        return None
    width = int.from_bytes(raw[16:20], "big")
    height = int.from_bytes(raw[20:24], "big")
    if width <= 0 or height <= 0:
        return None
    return {
        "width": width,
        "height": height,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _fits(box, size, margin):
    """Indica se a caixa cabe no canvas respeitando a margem."""
    width, height = int(size[0]), int(size[1])
    x, y = int(box.get("x", 0)), int(box.get("y", 0))
    w, h = int(box.get("w", 0)), int(box.get("h", 0))
    return (x >= margin and y >= margin
            and x + w <= width - margin and y + h <= height - margin)


def check_safe_area(boxes, size, safe_margin=SAFE_MARGIN) -> list:
    """Aponta caixas que invadem a zona segura do canvas."""
    issues = []
    margin = int(safe_margin)
    for box in boxes or []:
        if not _fits(box, size, margin):
            issues.append(_issue(
                "error", box.get("id"), "GATE_FAILED",
                "caixa fora da zona segura de %d px" % margin,
            ))
    return issues


def check_overflow(boxes, size) -> list:
    """Aponta caixas que passam da borda do canvas (encostar e permitido)."""
    issues = []
    width, height = int(size[0]), int(size[1])
    for box in boxes or []:
        x, y = int(box.get("x", 0)), int(box.get("y", 0))
        w, h = int(box.get("w", 0)), int(box.get("h", 0))
        if x < 0 or y < 0 or x + w > width or y + h > height:
            issues.append(_issue(
                "error", box.get("id"), "GATE_FAILED",
                "caixa estoura o canvas %dx%d" % (width, height),
            ))
    return issues


def _zone_px(zone, size):
    """Converte fracoes de zona segura em pixels, arredondando para cima."""
    if not isinstance(zone, dict):
        raise ForjaError("CONFIG_INVALID", "zona segura ausente ou invalida")
    vals = {}
    for key in ("top", "bottom", "left", "right"):
        val = zone.get(key)
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise ForjaError("CONFIG_INVALID", "zona segura invalida em %r: use fracao numerica" % key)
        if not 0 <= val < 0.5:
            raise ForjaError("CONFIG_INVALID", "zona segura invalida em %r: use fracao entre 0 e 0.5" % key)
        vals[key] = val
    width, height = int(size[0]), int(size[1])
    return (math.ceil(vals["top"] * height), math.ceil(vals["bottom"] * height),
            math.ceil(vals["left"] * width), math.ceil(vals["right"] * width))


def check_safe_zone(boxes, size, safe_zone) -> list:
    """Aponta caixas que invadem a zona segura em fracoes (encostar passa)."""
    top, bottom, left, right = _zone_px(safe_zone, size)
    width, height = int(size[0]), int(size[1])
    issues = []
    for box in boxes or []:
        x, y = int(box.get("x", 0)), int(box.get("y", 0))
        w, h = int(box.get("w", 0)), int(box.get("h", 0))
        if x < left or y < top or x + w > width - right or y + h > height - bottom:
            issues.append(_issue(
                "error", box.get("id"), "GATE_FAILED",
                "caixa fora da zona segura (top=%d bottom=%d left=%d right=%d)"
                % (top, bottom, left, right),
            ))
    return issues
