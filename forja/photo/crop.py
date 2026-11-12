"""Recorte determinístico por ponto focal (plano N-19).

Recorta a maior área da origem com o aspecto do alvo, centrada no ponto focal
normalizado (com clamp em 0..1 e nas bordas) e entrega o tamanho exato com
LANCZOS por padrão.
"""
from __future__ import annotations

from PIL import Image

from forja.errors import ForjaError


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def crop_focal(img: Image.Image, focal, target, *, resample=None) -> Image.Image:
    """Recorta `img` no ponto focal normalizado e reduz para `target` exato."""
    if resample is None:
        resample = Image.Resampling.LANCZOS
    width, height = img.size
    target_w, target_h = target
    if target_w > width or target_h > height:
        raise ForjaError("USAGE", "alvo não pode ampliar a origem",
                         details={"source": [width, height],
                                  "target": [target_w, target_h]})
    fx, fy = (max(0.0, min(1.0, float(v))) for v in focal)
    crop_w = min(float(width), height * target_w / target_h)
    crop_h = min(float(height), width * target_h / target_w)
    left = _clamp(fx * width - crop_w / 2, 0.0, width - crop_w)
    top = _clamp(fy * height - crop_h / 2, 0.0, height - crop_h)
    box = (round(left), round(top), round(left + crop_w), round(top + crop_h))
    out = img.crop(box)
    if out.size != (target_w, target_h):
        out = out.resize((target_w, target_h), resample)
    return out
