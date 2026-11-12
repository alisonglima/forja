"""Redução de ruído e nitidez determinísticas de foto (plano N-21).

Aplica mediana (sal-e-pimenta) e unsharp em CPU, sem mudar o tamanho nem o
modo RGB; a imagem de origem não é alterada. Não lê arquivo nem JSON.
"""
from __future__ import annotations

from PIL import Image, ImageFilter

from forja.errors import ForjaError


def _median_size(denoise) -> int:
    """Tamanho ímpar da mediana; ``denoise <= 1`` desliga a redução de ruído."""
    size = int(denoise)
    if size <= 1:
        return 0
    return size if size % 2 else size + 1


def _validated(img) -> Image.Image:
    if not isinstance(img, Image.Image):
        raise ForjaError(
            "MISSING_INPUT",
            "denoise_sharpen espera uma imagem Pillow",
            hint="carregue a foto com PIL.Image.open e tente de novo",
        )
    if img.mode != "RGB":
        raise ForjaError(
            "MISSING_INPUT",
            f"modo de imagem nao suportado: {img.mode}",
            hint="converta a foto para RGB antes de chamar denoise_sharpen",
            details={"mode": img.mode},
        )
    return img


def denoise_sharpen(img: Image.Image, *, denoise=3, sharpen=0.6) -> Image.Image:
    """Aplica mediana e unsharp, devolvendo uma cópia RGB do mesmo tamanho."""
    source = _validated(img)
    out = source.copy()
    size = _median_size(denoise)
    if size:
        out = out.filter(ImageFilter.MedianFilter(size=size))
    percent = int(round(float(sharpen) * 100))
    if percent > 0:
        out = out.filter(ImageFilter.UnsharpMask(radius=1, percent=percent,
                                                 threshold=0))
    return out
