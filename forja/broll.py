"""Validacao de b-roll 9:16/1080p e timeline de video.

`probe=` e injetavel; sem rede nem relogio real. O Flow entrega 1080x1920.
"""
from __future__ import annotations

import math
from pathlib import Path

from forja import probe as probe_mod
from forja.errors import ForjaError

WIDTH, HEIGHT = 1080, 1920
RATIO = WIDTH / HEIGHT
RATIO_TOL = 0.01
ASSET_MISSING, ASSET_OUTSIDE = "ASSET_MISSING", "ASSET_OUTSIDE"
MEDIA_BYTES, MEDIA_PIXELS, MEDIA_RATIO = "MEDIA_BYTES", "MEDIA_PIXELS", "MEDIA_RATIO"


def _issue(label, code, msg):
    return {"level": "error", "id": label, "code": code, "msg": msg}


def _label(value):
    return Path(value).name if isinstance(value, str) and value else ""


def _target(root, value):
    """Resolve `value` sob `root`; `None` quando o caminho escapa da raiz."""
    root_path = Path(root or ".").resolve()
    path = Path(value)
    if path.is_absolute():
        return None
    target = (root_path / path).resolve()
    return target if target.is_relative_to(root_path) else None


def validate_broll(path, root=None, probe=None):
    """Valida um b-roll existente contra 1080x1920 e devolve as issues."""
    label = _label(path)
    if not isinstance(path, str) or not path.strip():
        return [_issue(label, ASSET_MISSING, "b-roll sem caminho")]
    target = _target(root, path)
    if target is None:
        return [_issue(label, ASSET_OUTSIDE, "b-roll fora da raiz: %s" % path)]
    if not target.is_file():
        return [_issue(label, ASSET_MISSING, "arquivo nao encontrado: %s" % path)]
    probe = probe or probe_mod.probe_video
    try:
        data = probe(target)
    except (OSError, RuntimeError, TypeError, ValueError, KeyError) as exc:
        return [_issue(label, MEDIA_BYTES, "midia ilegivel: %s" % exc)]
    if not isinstance(data, dict):
        return [_issue(label, MEDIA_BYTES, "medidas ausentes ou invalidas")]
    width, height = data.get("width"), data.get("height")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (width, height)):
        return [_issue(label, MEDIA_PIXELS, "dimensoes invalidas: %r x %r" % (width, height))]
    if height <= 0 or abs(width / height - RATIO) > RATIO_TOL:
        return [_issue(label, MEDIA_RATIO, "%dx%d nao esta em 9:16" % (width, height))]
    if width != WIDTH or height != HEIGHT:
        return [_issue(label, MEDIA_PIXELS, "%dx%d (esperado %dx%d)" % (
            width, height, WIDTH, HEIGHT))]
    return []


def _fail(code, msg, **details):
    raise ForjaError(code, msg, details=details or None)


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _asset(value):
    if not isinstance(value, str) or not value.strip():
        _fail("CONFIG_INVALID", "segmento sem asset")
    if Path(value).is_absolute() or ".." in Path(value).parts:
        _fail("CONFIG_INVALID", "caminho de asset fora da raiz: %r" % value)
    return value


def _cut(value, available):
    if value is None:
        return None
    if not isinstance(value, dict):
        _fail("CONFIG_INVALID", "corte deve ser um mapeamento")
    start, end = _number(value.get("in")), _number(value.get("out"))
    if start is None or end is None or not 0 <= start < end <= available:
        _fail("CONFIG_INVALID", "corte invalido para o asset")
    return start, end


def build_timeline(segmentos, assets):
    """Monta a timeline contigua na ordem dos segmentos."""
    if not isinstance(segmentos, list) or not segmentos or not isinstance(assets, dict):
        _fail("CONFIG_INVALID", "timeline e assets devem ser preenchidos")
    segments = []
    cursor = 0.0
    for index, segment in enumerate(segmentos):
        if not isinstance(segment, dict):
            _fail("CONFIG_INVALID", "segmento %d deve ser um mapeamento" % index)
        scene_id = segment.get("id")
        if not isinstance(scene_id, str) or not scene_id.strip():
            _fail("CONFIG_INVALID", "segmento %d sem id" % index)
        asset = _asset(segment.get("asset"))
        if asset not in assets:
            _fail("MISSING_INPUT", "asset ausente: %s" % asset, asset=asset)
        meta = assets[asset]
        available = _number(meta.get("duration")) if isinstance(meta, dict) else None
        if available is None:
            _fail("MISSING_INPUT", "asset sem duration: %s" % asset, asset=asset)
        duration = _number(segment.get("duracao_s"))
        if duration is None or duration <= 0:
            _fail("CONFIG_INVALID", "duracao_s deve ser positiva")
        cut = _cut(segment.get("corte"), available)
        end = cursor + duration
        item = {"id": scene_id, "asset": asset, "start": cursor, "end": end,
                "duration": duration, "texto": segment.get("texto")}
        if cut is not None:
            item["cut_in"], item["cut_out"] = cut
        segments.append(item)
        cursor = end
    return {"segments": segments, "total_s": cursor}


def _timestamp(seconds):
    total_ms = max(0, int(round((_number(seconds) or 0.0) * 1000)))
    hours, remainder = divmod(total_ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, millis = divmod(remainder, 1000)
    return "%02d:%02d:%02d,%03d" % (hours, minutes, secs, millis)


def to_srt(timeline):
    """Gera um bloco SRT por segmento, respeitando a ordem da timeline."""
    segments = timeline.get("segments") if isinstance(timeline, dict) else None
    if not isinstance(segments, list):
        return ""
    blocks = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        text = segment.get("texto")
        text = "" if text is None else str(text)
        blocks.append("%d\n%s --> %s\n%s" % (
            len(blocks) + 1, _timestamp(segment.get("start")),
            _timestamp(segment.get("end")), text))
    return "\n\n".join(blocks)
