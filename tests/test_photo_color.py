"""Contrato de `forja.photo.color.apply_cube` (somente o que o plano diz).

- plano:773 congela `forja.photo.color: apply_cube(img, lut_path, strength=1.0) -> Image.Image`.
- plano:746 descreve `color.py` (NOVO): aplica `.cube` 3D com interpolacao trilinear e forca.
- plano:812 (N-20 `L-PHOTO-COLOR-01`) entrega `forja/photo/color.py` e aceita este teste.
- plano:844 (T-PHOTO-COLOR `L-T-PCO-01`) define este arquivo e o `acceptance` `--collect-only`.
- plano:102/746: o `.cube` e os parametros vem do manifesto da marca (`brands/<id>/luts/`).
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _solid(color=(255, 0, 0), size=(4, 4)):
    Image = pytest.importorskip("PIL.Image")
    return Image.new("RGB", size, color)


def _write_cube(path: Path, entries=None, size: int = 2) -> Path:
    if entries is None:  # identidade SIZE 2 (R varia mais rapido)
        entries = [f"{r}.0 {g}.0 {b}.0" for b in (0, 1) for g in (0, 1) for r in (0, 1)]
    text = f'TITLE "t"\nLUT_3D_SIZE {size}\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n'
    path.write_text(text + "\n".join(entries) + "\n", encoding="utf-8")
    return path


def test_identity_lut_keeps_pixels(tmp_path):
    from PIL import Image as PILImage
    from forja.photo import color

    img = _solid()
    out = color.apply_cube(img, str(_write_cube(tmp_path / "id.cube")), strength=1.0)
    assert isinstance(out, PILImage.Image)
    assert out.size == img.size and out.mode == img.mode
    assert list(out.getdata()) == list(img.getdata())


def test_full_strength_applies_lut(tmp_path):
    from forja.photo import color

    img = _solid((255, 0, 0))
    lut = _write_cube(tmp_path / "blue.cube", entries=["0.0 0.0 1.0"] * 8)
    out = color.apply_cube(img, str(lut), strength=1.0)
    assert list(out.getdata()) == [(0, 0, 255)] * 16


def test_strength_zero_returns_original(tmp_path):
    from forja.photo import color

    img = _solid((255, 0, 0))
    lut = _write_cube(tmp_path / "blue.cube", entries=["0.0 0.0 1.0"] * 8)
    out = color.apply_cube(img, str(lut), strength=0.0)
    assert list(out.getdata()) == list(img.getdata())


def test_default_strength_equals_full(tmp_path):
    from forja.photo import color

    img = _solid((255, 0, 0))
    lut = _write_cube(tmp_path / "blue.cube", entries=["0.0 0.0 1.0"] * 8)
    assert list(color.apply_cube(img, str(lut)).getdata()) == [(0, 0, 255)] * 16


def test_missing_lut_raises(tmp_path):
    from forja.photo import color

    with pytest.raises(Exception):
        color.apply_cube(_solid(), str(tmp_path / "nao-existe.cube"))


def test_truncated_cube_raises(tmp_path):
    from forja.photo import color

    lut = tmp_path / "bad.cube"
    lut.write_text('TITLE "x"\nLUT_3D_SIZE 2\n', encoding="utf-8")
    with pytest.raises(Exception):
        color.apply_cube(_solid(), str(lut))


def test_none_image_raises(tmp_path):
    from forja.photo import color

    with pytest.raises(Exception):
        color.apply_cube(None, str(_write_cube(tmp_path / "id.cube")))


def test_wrong_lut_type_raises():
    from forja.photo import color

    with pytest.raises(Exception):
        color.apply_cube(_solid(), 123)


def test_dotdot_lut_raises(tmp_path):
    from forja.photo import color

    with pytest.raises(Exception):
        color.apply_cube(_solid(), str(tmp_path / ".." / "fora.cube"))


# LACUNA: o contrato nao nomeia tipo/codigo de erro, faixa/clamp de `strength`,
# nem tolerancia de arredondamento da interpolacao trilinear.
