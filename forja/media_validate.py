"""Validacao deterministica de midia contra a linha de `formats.json`.

Devolve issues no formato de `forja.qa` (`level`, `code`, `msg`); os codigos
sao issues de modulo e nao entram em `ERROR_CODES`.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from forja import probe
from forja.errors import ForjaError

MEDIA_BYTES = "MEDIA_BYTES"
MEDIA_PIXELS = "MEDIA_PIXELS"
MEDIA_RATIO = "MEDIA_RATIO"
MEDIA_FORMAT = "MEDIA_FORMAT"

_RATIO_TOL = 0.01
_RATIO_RE = re.compile(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)")
_IMAGE_PREFIXES = (
    b"\x89PNG\r\n\x1a\n",
    b"\xff\xd8\xff",
    b"GIF87a",
    b"GIF89a",
)
_VIDEO_PREFIXES = (b"\x1aE\xdf\xa3", b"\x00\x00\x01", b"FLV")


def _issue(code: str, msg: str) -> dict:
    return {"level": "error", "code": code, "msg": msg}


def _kind(head: bytes) -> str | None:
    """Classifica o arquivo pelo magic bytes: `still`, `video` ou `None`."""
    if any(head.startswith(prefix) for prefix in _IMAGE_PREFIXES):
        return "still"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "still"
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return "video"
    if any(head.startswith(prefix) for prefix in _VIDEO_PREFIXES):
        return "video"
    if head[:4] == b"RIFF" and head[8:12] == b"AVI ":
        return "video"
    return None


def _ratio(value) -> float | None:
    """Le a razao `a:b` (primeiro par) ou um numero ja pronto."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, str):
        return None
    match = _RATIO_RE.search(value)
    if match is None:
        return None
    num = float(match.group(1))
    den = float(match.group(2))
    if den == 0:
        return None
    return num / den


def _dimensions(path: Path) -> tuple[int, int] | None:
    """Abre o still com Pillow; `None` quando os bytes nao decodificam."""
    try:
        with Image.open(path) as image:
            width, height = image.size
            image.load()
    except (OSError, ValueError, SyntaxError):
        return None
    return int(width), int(height)


def _probe_dimensions(path: Path) -> tuple[int, int] | None:
    """Le dimensoes do video via `probe.probe_video` (injetavel no teste)."""
    try:
        data = probe.probe_video(path)
        return int(data["width"]), int(data["height"])
    except (KeyError, TypeError, ValueError, RuntimeError, OSError):
        return None


def _as_int(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_media(path, spec) -> list[dict]:
    """Valida tamanho, pixels, razao e formato de `path` contra `spec`."""
    if not isinstance(spec, dict):
        raise ForjaError("CONFIG_INVALID", "spec de midia deve ser um dict")

    path = Path(path)
    try:
        with path.open("rb") as fh:
            head = fh.read(12)
        size = path.stat().st_size
    except OSError as exc:
        return [_issue(MEDIA_FORMAT, "nao foi possivel ler %s: %s" % (path.name, exc))]

    kind = _kind(head)
    if kind is None:
        return [_issue(MEDIA_FORMAT, "%s nao tem magic bytes de imagem ou video" % path.name)]

    if kind == "still":
        dims = _dimensions(path)
    else:
        dims = _probe_dimensions(path)
    if dims is None:
        return [_issue(MEDIA_FORMAT, "formato de %s invalido ou truncado" % path.name)]

    issues: list[dict] = []
    limit = _as_int(spec.get("limite_bytes"))
    if limit is not None and size > limit:
        issues.append(_issue(
            MEDIA_BYTES,
            "%s tem %d bytes (limite %d)" % (path.name, size, limit),
        ))

    width, height = dims
    expected_w = _as_int(spec.get("largura"))
    expected_h = _as_int(spec.get("altura"))
    if ((expected_w is not None and width != expected_w)
            or (expected_h is not None and height != expected_h)):
        issues.append(_issue(
            MEDIA_PIXELS,
            "%s tem %dx%d (esperado %sx%s)" % (
                path.name, width, height,
                expected_w if expected_w is not None else "?",
                expected_h if expected_h is not None else "?",
            ),
        ))

    expected_ratio = _ratio(spec.get("razao"))
    if expected_ratio is not None and height > 0:
        actual_ratio = width / height
        if abs(actual_ratio - expected_ratio) > _RATIO_TOL:
            issues.append(_issue(
                MEDIA_RATIO,
                "%s tem razao %.4f (esperado %.4f)" % (
                    path.name, actual_ratio, expected_ratio,
                ),
            ))

    return issues
