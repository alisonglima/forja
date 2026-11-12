"""Contrato de `forja.photo.duotone` (L-T-PDU-01).
`plano:775`: `duotone(img, dark, light) -> Image.Image` e
`blend(img, overlay, alpha=0.5) -> Image.Image`.
`plano:746`: duotone mapeia a luminancia para um gradiente entre as cores da
marca; blend compoe o overlay com peso alpha; o pipeline e deterministico.
LACUNA: o plano nao decide o formato das cores (hex vs tupla RGB) nem a caixa;
congelamos hex `#RRGGBB` minusculo. Tambem nao decide alpha fora de [0, 1],
tamanhos diferentes, RGBA/alfa, espaco de luminancia (BT.601 vs linear) nem
erro/tipo para entradas invalidas; nada disso e congelado aqui.
"""
from __future__ import annotations


def _image(colors):
    from PIL import Image
    img = Image.new("RGB", (len(colors), 1))
    img.putdata(colors)
    return img


def _pixels(img):
    return list(img.getdata())


def test_duotone_returns_rgb_image_with_same_size():
    from PIL import Image
    from forja.photo.duotone import duotone
    out = duotone(Image.new("RGB", (3, 2), (0, 0, 0)), "#101020", "#f0e0d0")
    assert isinstance(out, Image.Image)
    assert (out.size, out.mode) == ((3, 2), "RGB")


def test_duotone_maps_luminance_to_dark_light_gradient():
    from forja.photo.duotone import duotone
    out = duotone(_image([(0, 0, 0), (64, 64, 64), (192, 192, 192), (255, 255, 255)]),
                  "#101020", "#f0e0d0")
    assert out.getpixel((0, 0)) == (0x10, 0x10, 0x20)
    assert out.getpixel((3, 0)) == (0xF0, 0xE0, 0xD0)
    assert 0x10 < out.getpixel((1, 0))[0] < out.getpixel((2, 0))[0] < 0xF0


def test_duotone_with_equal_endpoints_is_flat():
    from forja.photo.duotone import duotone
    out = duotone(_image([(0, 0, 0), (128, 128, 128), (255, 255, 255)]),
                  "#336699", "#336699")
    assert _pixels(out) == [(0x33, 0x66, 0x99)] * 3


def test_blend_returns_rgb_image_with_same_size():
    from PIL import Image
    from forja.photo.duotone import blend
    out = blend(Image.new("RGB", (3, 2), (10, 20, 30)),
                Image.new("RGB", (3, 2), (200, 100, 50)))
    assert isinstance(out, Image.Image)
    assert (out.size, out.mode) == ((3, 2), "RGB")


def test_blend_default_alpha_is_half():
    from forja.photo.duotone import blend
    base, overlay = _image([(10, 20, 30)]), _image([(200, 100, 50)])
    assert _pixels(blend(base, overlay)) == _pixels(blend(base, overlay, 0.5))


def test_blend_half_alpha_mixes_channels():
    from forja.photo.duotone import blend
    out = blend(_image([(10, 20, 30)]), _image([(200, 100, 50)]))
    assert out.getpixel((0, 0)) == (105, 60, 40)


def test_blend_alpha_weights_overlay():
    from forja.photo.duotone import blend
    base, overlay = _image([(10, 20, 30)]), _image([(210, 100, 50)])
    assert _pixels(blend(base, overlay, 0.0)) == _pixels(base)
    assert blend(base, overlay, 0.25).getpixel((0, 0)) == (60, 40, 35)
    assert _pixels(blend(base, overlay, 1.0)) == _pixels(overlay)


def test_duotone_is_deterministic():
    from forja.photo.duotone import duotone
    src = _image([(0, 0, 0), (128, 128, 128), (255, 255, 255)])
    first = duotone(src, "#112233", "#ddeeff")
    assert first.tobytes() == duotone(src, "#112233", "#ddeeff").tobytes()


def test_blend_is_deterministic():
    from forja.photo.duotone import blend
    src = _image([(0, 0, 0), (128, 128, 128), (255, 255, 255)])
    first = blend(src, src, 0.3)
    assert first.tobytes() == blend(src, src, 0.3).tobytes()
