"""Contraste de texto sobre foto/frame (plano N-15).

Recorta a caixa sob o texto, calcula a razao de contraste sRGB pixel a pixel
e resume minimo/p5/media contra o limite. Para video, extrai um frame por
timestamp com `ffmpeg`, usando `run=` injetavel.
"""
from __future__ import annotations

import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from forja import env as envmod
from forja.errors import ForjaError

# Coeficientes de luminancia relativa sRGB (REC. 709 / WCAG).
_LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)


def _usage(msg, **details) -> ForjaError:
    return ForjaError("USAGE", msg, details=details or None)


def _parse_color(text_color) -> np.ndarray:
    """Converte `#RGB`/`#RRGGBB` em tres canais de 0 a 255."""
    if not isinstance(text_color, str):
        raise _usage("text_color deve ser hexadecimal #RRGGBB",
                     text_color=repr(text_color))
    value = text_color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise _usage("text_color deve ser hexadecimal #RRGGBB", text_color=text_color)
    try:
        channels = [int(value[i:i + 2], 16) for i in (0, 2, 4)]
    except ValueError as exc:
        raise _usage("text_color deve ser hexadecimal #RRGGBB",
                     text_color=text_color) from exc
    return np.asarray(channels, dtype=np.float64)


def _linear(channels) -> np.ndarray:
    """Converte sRGB [0,255] para luz linear."""
    c = np.asarray(channels, dtype=np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _luminance(rgb) -> np.ndarray:
    """Luminancia relativa sRGB; aceita (..., 3) e devolve (...)."""
    return _linear(rgb) @ _LUMA


def _as_image(image) -> np.ndarray:
    if not isinstance(image, np.ndarray):
        raise _usage("image deve ser ndarray HxWx3 (ou HxWx4)",
                     type=type(image).__name__)
    if image.ndim != 3 or image.shape[2] not in (3, 4):
        raise _usage("image deve ser ndarray HxWx3 (ou HxWx4)",
                     shape=tuple(image.shape))
    if image.shape[0] == 0 or image.shape[1] == 0:
        raise _usage("image vazia", shape=tuple(image.shape))
    return image[..., :3].astype(np.float64, copy=False)


def _box(box, width: int, height: int) -> tuple[int, int, int, int]:
    """Normaliza `(x0, y0, x1, y1)`, recortando aos limites da imagem."""
    if not isinstance(box, (tuple, list)) or len(box) != 4:
        raise _usage("box deve ser (x0, y0, x1, y1)", box=repr(box))
    try:
        x0, y0, x1, y1 = (int(v) for v in box)
    except (TypeError, ValueError) as exc:
        raise _usage("box deve conter quatro numeros", box=repr(box)) from exc
    x0, y0 = max(0, min(width, x0)), max(0, min(height, y0))
    x1, y1 = max(0, min(width, x1)), max(0, min(height, y1))
    if x1 <= x0 or y1 <= y0:
        raise _usage("box vazia: nao ha regiao sob o texto",
                     box=[x0, y0, x1, y1], image=[width, height])
    return x0, y0, x1, y1


def _step(sample_step) -> int:
    try:
        step = int(sample_step)
    except (TypeError, ValueError) as exc:
        raise _usage("sample_step deve ser inteiro >= 1") from exc
    if step < 1:
        raise _usage("sample_step deve ser inteiro >= 1")
    return step


def photo_contrast(image, box, text_color, min_ratio=4.5, sample_step=2) -> dict:
    """Razao de contraste do texto contra a regiao `box` da imagem.

    Devolve `min`, `p5`, `mean` e `pass`; a reprovacao usa o minimo, o caso
    mais conservador da regiao.
    """
    rgb = _as_image(image)
    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = _box(box, width, height)
    step = _step(sample_step)
    text_luma = float(_luminance(_parse_color(text_color)))

    luma = _luminance(rgb[y0:y1, x0:x1])[::step, ::step]
    if luma.size == 0:
        raise _usage("box vazia depois da amostragem")
    ratios = (np.maximum(luma, text_luma) + 0.05) / (np.minimum(luma, text_luma) + 0.05)

    minimum = float(np.min(ratios))
    return {
        "min": minimum,
        "p5": float(np.percentile(ratios, 5)),
        "mean": float(np.mean(ratios)),
        "pass": bool(minimum >= float(min_ratio)),
    }


def check_photo_contrast(image, box, text_color, min_ratio=4.5, sample_step=2) -> list[dict]:
    """Issue `CONTRAST_PHOTO` no formato de `qa.py` quando o texto reprova."""
    result = photo_contrast(image, box, text_color, min_ratio=min_ratio,
                            sample_step=sample_step)
    if result["pass"]:
        return []
    return [{
        "level": "error",
        "id": "photo_contrast",
        "code": "CONTRAST_PHOTO",
        "msg": "contraste minimo %.2f:1 abaixo de %.1f:1 (media %.2f:1)"
               % (result["min"], float(min_ratio), result["mean"]),
    }]


def _run_ffmpeg(cmd, run) -> None:
    """Executa `cmd` e transforma falha de ffmpeg em `ForjaError`."""
    try:
        result = run(cmd, capture_output=True, text=True, env=envmod.sanitized())
    except FileNotFoundError as exc:
        raise ForjaError(
            "MISSING_PREREQ", "ffmpeg nao encontrado: ffmpeg",
            hint="instale ffmpeg e ponha no PATH", details={"error": str(exc)},
        ) from exc
    if result.returncode != 0:
        stderr = result.stderr or ""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        raise ForjaError(
            "PROVIDER_ERROR",
            "ffmpeg falhou ao extrair frame (exit %d)" % result.returncode,
            details={"returncode": result.returncode, "stderr_tail": stderr[-500:]},
        )


def video_frame(path, at_s, run=subprocess.run) -> bytes:
    """Extrai um frame PNG em `at_s` segundos via `ffmpeg` (sem Chrome)."""
    try:
        at = float(at_s)
    except (TypeError, ValueError) as exc:
        raise _usage("at_s deve ser numerico") from exc
    if not math.isfinite(at) or at < 0:
        raise _usage("at_s deve ser um numero finito >= 0")

    with tempfile.TemporaryDirectory(prefix="forja-frame-") as tmp:
        out = Path(tmp) / "frame.png"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", str(at), "-i", str(path),
            "-frames:v", "1", "-f", "image2", "-vcodec", "png", str(out),
        ]
        _run_ffmpeg(cmd, run)
        try:
            data = out.read_bytes()
        except OSError as exc:
            raise ForjaError(
                "PROVIDER_ERROR", "ffmpeg nao gerou o frame",
                details={"path": str(path), "at_s": at, "error": str(exc)},
            ) from exc
    if not data:
        raise ForjaError("PROVIDER_ERROR", "ffmpeg gerou frame vazio",
                         details={"path": str(path), "at_s": at})
    return data
