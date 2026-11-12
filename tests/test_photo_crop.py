"""Contrato de `forja.photo.crop.crop_focal` (L-T-PC-01).
`plano:772`: assinatura `crop_focal(img, focal, target, *, resample=None) -> Image.Image`.
`plano:746`: focal normalizado, alvo exato com LANCZOS, clamp e determinismo
(mesma entrada/parâmetros => mesmos bytes).
LACUNA: o plano não define erro/tipo para `img`, `focal` ou `target` inválidos
(alvo 0/negativo, focal NaN) nem modo L/RGBA; nada disso é congelado. Também não
congelamos target maior que a origem (plano:746 veta ampliação local).
"""
from __future__ import annotations


def _gradient(width, height):
    from PIL import Image
    img = Image.new("RGB", (width, height))
    img.putdata([(x * 3 % 256, y * 5 % 256, (x + y) * 7 % 256)
                 for y in range(height) for x in range(width)])
    return img


def _striped():
    from PIL import Image
    img = Image.new("RGB", (8, 4))
    img.putdata([(255, 0, 0) if x % 2 == 0 else (0, 0, 255)
                 for y in range(4) for x in range(8)])
    return img


def _bands(horizontal):
    from PIL import Image
    colors = [(255, 0, 0)] * 30 + [(0, 255, 0)] * 30 + [(0, 0, 255)] * 30
    width, height = (90, 30) if horizontal else (30, 90)
    img = Image.new("RGB", (width, height))
    img.putdata(colors * 30 if horizontal else [c for c in colors for _ in range(30)])
    return img


def test_returns_image_at_exact_target_size():
    from PIL import Image
    from forja.photo.crop import crop_focal

    out = crop_focal(Image.new("RGB", (40, 30), (10, 20, 30)), (0.5, 0.5), (7, 5))
    assert isinstance(out, Image.Image)
    assert out.size == (7, 5)


def test_same_aspect_keeps_full_frame():
    from forja.photo.crop import crop_focal

    source = _gradient(9, 7)
    assert crop_focal(source, (0.5, 0.5), (9, 7)).tobytes() == source.tobytes()


def test_corner_focal_clamps_crop_box_to_image():
    from forja.photo.crop import crop_focal

    source = _gradient(40, 40)
    assert crop_focal(source, (0.0, 0.0), (40, 40)).tobytes() == source.tobytes()


def test_normalized_focal_selects_x_and_y_regions():
    from forja.photo.crop import crop_focal

    horizontal = _bands(True)
    vertical = _bands(False)
    assert crop_focal(horizontal, (0.0, 0.5), (30, 30)).getpixel((15, 15)) == (255, 0, 0)
    assert crop_focal(horizontal, (1.0, 0.5), (30, 30)).getpixel((15, 15)) == (0, 0, 255)
    assert crop_focal(vertical, (0.5, 0.0), (30, 30)).getpixel((15, 15)) == (255, 0, 0)
    assert crop_focal(vertical, (0.5, 1.0), (30, 30)).getpixel((15, 15)) == (0, 0, 255)


def test_focal_outside_unit_range_is_clamped():
    from forja.photo.crop import crop_focal

    source = _gradient(90, 90)
    top_left = crop_focal(source, (0.0, 0.0), (30, 30))
    bottom_right = crop_focal(source, (1.0, 1.0), (30, 30))
    assert crop_focal(source, (-0.5, -0.5), (30, 30)).tobytes() == top_left.tobytes()
    assert crop_focal(source, (1.5, 1.5), (30, 30)).tobytes() == bottom_right.tobytes()


def test_resample_defaults_to_lanczos_and_honors_override():
    from PIL import Image
    from forja.photo.crop import crop_focal

    source = _striped()
    default = crop_focal(source, (0.5, 0.5), (4, 2))
    lanczos = crop_focal(source, (0.5, 0.5), (4, 2), resample=Image.Resampling.LANCZOS)
    nearest = crop_focal(source, (0.5, 0.5), (4, 2), resample=Image.Resampling.NEAREST)
    assert default.tobytes() == lanczos.tobytes()
    assert nearest.tobytes() != lanczos.tobytes()


def test_same_inputs_produce_identical_bytes():
    from forja.photo.crop import crop_focal

    source = _gradient(60, 40)
    first = crop_focal(source, (0.25, 0.75), (16, 9))
    second = crop_focal(source, (0.25, 0.75), (16, 9))
    assert first.tobytes() == second.tobytes()
