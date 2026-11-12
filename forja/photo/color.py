"""Aplica LUT 3D `.cube` a fotos (plano N-20).

Interpolacao trilinear com forca opcional. O `.cube` vem do manifesto da
marca (`brands/<id>/luts/`); nada e gerado, baixado ou medido aqui.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
from PIL import Image

from forja.errors import ForjaError


def _fail(code, msg, **details):
    raise ForjaError(code, msg, details=details or None)


def _triple(parts, key):
    """Le tres numeros de uma linha `DOMAIN_MIN`/`DOMAIN_MAX`."""
    if len(parts) != 4:
        _fail("USAGE", f"{key} espera tres numeros", line=" ".join(parts))
    try:
        return np.asarray([float(v) for v in parts[1:]], dtype=np.float64)
    except ValueError as exc:
        raise ForjaError("USAGE", f"{key} contem valor nao numerico",
                         details={"line": " ".join(parts)}) from exc


def _parse_cube(text: str) -> tuple[np.ndarray, int, np.ndarray, np.ndarray]:
    """Le o `.cube` e devolve `(lut, size, domain_min, domain_max)`.

    `lut` tem eixos `[b, g, r, canal]`: o `.cube` lista R mais rapido.
    """
    size = None
    domain_min = np.zeros(3, dtype=np.float64)
    domain_max = np.ones(3, dtype=np.float64)
    rows = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        key = parts[0].upper()
        if key == "TITLE":
            continue
        if key == "LUT_3D_SIZE":
            if len(parts) != 2:
                _fail("USAGE", "LUT_3D_SIZE espera um inteiro", line=line)
            try:
                size = int(parts[1])
            except ValueError as exc:
                raise ForjaError("USAGE", "LUT_3D_SIZE invalido",
                                 details={"line": line}) from exc
            if size < 1:
                _fail("USAGE", "LUT_3D_SIZE deve ser >= 1", size=size)
        elif key == "DOMAIN_MIN":
            domain_min = _triple(parts, key)
        elif key == "DOMAIN_MAX":
            domain_max = _triple(parts, key)
        elif key.startswith("LUT_"):
            _fail("USAGE", "apenas LUT_3D_SIZE e suportado", line=line)
        else:
            if len(parts) != 3:
                _fail("USAGE", "entrada do LUT deve ter tres canais", line=line)
            try:
                rows.append([float(v) for v in parts])
            except ValueError as exc:
                raise ForjaError("USAGE", "entrada do LUT nao numerica",
                                 details={"line": line}) from exc

    if size is None:
        _fail("MISSING_INPUT", "LUT sem LUT_3D_SIZE")
    expected = size ** 3
    if len(rows) != expected:
        _fail("MISSING_INPUT", "LUT truncado ou com entradas demais",
              expected=expected, found=len(rows))
    if np.any(domain_max <= domain_min):
        _fail("USAGE", "DOMAIN_MAX deve ser maior que DOMAIN_MIN")

    lut = np.asarray(rows, dtype=np.float64).reshape(size, size, size, 3)
    return lut, size, domain_min, domain_max


def _load_cube(lut_path) -> tuple[np.ndarray, int, np.ndarray, np.ndarray]:
    """Valida o caminho e le o LUT; nunca aceita `..` nem tipo estranho."""
    if not isinstance(lut_path, (str, os.PathLike)):
        _fail("USAGE", "lut_path deve ser caminho de arquivo .cube",
              type=type(lut_path).__name__)
    path = Path(lut_path)
    if ".." in path.parts:
        _fail("USAGE", "lut_path nao pode conter '..'", path=str(path))
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ForjaError("MISSING_INPUT", "LUT nao encontrado ou ilegivel",
                         details={"path": str(path)}) from exc
    return _parse_cube(text)


def _array(img):
    """Valida a imagem e devolve `(rgb_uint8, alpha_ou_None)`."""
    if not isinstance(img, Image.Image):
        _fail("USAGE", "img deve ser PIL.Image.Image",
              type=type(img).__name__)
    if img.mode not in ("RGB", "RGBA"):
        _fail("USAGE", "img deve estar em RGB ou RGBA", mode=img.mode)
    arr = np.asarray(img, dtype=np.uint8)
    alpha = arr[..., 3].copy() if img.mode == "RGBA" else None
    return arr[..., :3].copy(), alpha


def _strength(value) -> float:
    """Forca em [0, 1]; fora da faixa e presa ao limite mais proximo."""
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ForjaError("USAGE", "strength deve ser numero entre 0 e 1",
                         details={"strength": repr(value)}) from exc
    if not math.isfinite(value):
        _fail("USAGE", "strength deve ser finito", strength=repr(value))
    return min(1.0, max(0.0, value))


def _trilinear(lut, size, domain_min, domain_max, rgb):
    """Interpola `rgb` (N, 3) em [0, 1] na grade do LUT."""
    span = domain_max - domain_min
    pos = np.clip((rgb - domain_min) / span, 0.0, 1.0) * (size - 1)
    lo = np.clip(np.floor(pos).astype(np.intp), 0, size - 1)
    hi = np.minimum(lo + 1, size - 1)
    frac = pos - lo

    b0, g0, r0 = lo[:, 2], lo[:, 1], lo[:, 0]
    b1, g1, r1 = hi[:, 2], hi[:, 1], hi[:, 0]
    fr, fg, fb = frac[:, 0:1], frac[:, 1:2], frac[:, 2:3]

    def mix(a, b, t):
        return a + (b - a) * t

    c00 = mix(lut[b0, g0, r0], lut[b0, g0, r1], fr)
    c01 = mix(lut[b0, g1, r0], lut[b0, g1, r1], fr)
    c10 = mix(lut[b1, g0, r0], lut[b1, g0, r1], fr)
    c11 = mix(lut[b1, g1, r0], lut[b1, g1, r1], fr)
    return mix(mix(c00, c01, fg), mix(c10, c11, fg), fb)


def apply_cube(img, lut_path, strength=1.0) -> Image.Image:
    """Aplica um LUT 3D `.cube` a `img`, misturando por `strength`."""
    rgb, alpha = _array(img)
    lut, size, domain_min, domain_max = _load_cube(lut_path)
    amount = _strength(strength)
    if amount == 0.0:
        return img.copy()

    height, width = rgb.shape[:2]
    source = rgb.reshape(-1, 3).astype(np.float64) / 255.0
    graded = _trilinear(lut, size, domain_min, domain_max, source)
    mixed = source * (1.0 - amount) + np.clip(graded, 0.0, 1.0) * amount
    out = np.rint(np.clip(mixed, 0.0, 1.0) * 255.0).astype(np.uint8)
    out = out.reshape(height, width, 3)
    if alpha is not None:
        out = np.dstack((out, alpha))
    return Image.fromarray(out)
