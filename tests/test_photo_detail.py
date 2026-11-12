"""Contrato de `forja.photo.detail` (plano:774, plano:746).

`denoise_sharpen(img, *, denoise=3, sharpen=0.6) -> Image.Image`, aplicado
antes do resize e sem mudar dimensoes (plano:102); deterministico (plano:746).
# LACUNA: 0/faixa de denoise e sharpen, erro para entrada nao-Image ou modo
# nao-RGB, algoritmo/raio do unsharp; o modulo nao le arquivo/JSON.
"""


def _image(pixels, width, height):
    from PIL import Image
    img = Image.new("RGB", (width, height))
    img.putdata(pixels)
    return img


def _speckled_rgb(width=32, height=24):
    """Fundo cinza uniforme com sal-e-pimenta: mede reducao de ruido."""
    pixels = [(128, 128, 128)] * (width * height)
    for i in range(0, len(pixels), 7):
        pixels[i] = (0, 0, 0)
    for i in range(3, len(pixels), 11):
        pixels[i] = (255, 255, 255)
    return _image(pixels, width, height)


def _textured_rgb(width=32, height=24):
    """Xadrez fino com jitter: da material para denoise e unsharp."""
    pixels = []
    for y in range(height):
        for x in range(width):
            base = 50 if (x // 3 + y // 3) % 2 == 0 else 200
            v = max(0, min(255, base + (x * 13 + y * 29) % 25 - 12))
            pixels.append((v, v, v))
    return _image(pixels, width, height)


def test_signature_freezes_keyword_only_defaults():
    import inspect
    from forja.photo import detail
    params = inspect.signature(detail.denoise_sharpen).parameters
    assert params["denoise"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["sharpen"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["denoise"].default == 3
    assert params["sharpen"].default == 0.6


def test_defaults_equal_explicit_default_arguments():
    from forja.photo import detail
    img = _textured_rgb()
    implicit = detail.denoise_sharpen(img)
    explicit = detail.denoise_sharpen(img, denoise=3, sharpen=0.6)
    assert implicit.tobytes() == explicit.tobytes()


def test_returns_independent_image_with_same_size_and_rgb_mode():
    from PIL import Image
    from forja.photo import detail
    img = _textured_rgb()
    original = img.tobytes()
    out = detail.denoise_sharpen(img)
    assert isinstance(out, Image.Image)
    assert out is not img
    assert out.size == img.size == (32, 24)
    assert out.mode == "RGB"
    assert img.tobytes() == original


def test_same_input_and_parameters_are_deterministic():
    from forja.photo import detail
    img = _textured_rgb()
    first = detail.denoise_sharpen(img, denoise=3, sharpen=0.6)
    second = detail.denoise_sharpen(img, denoise=3, sharpen=0.6)
    assert first.tobytes() == second.tobytes()


def test_denoise_reduces_speckle_spread():
    from PIL import ImageStat
    from forja.photo import detail
    img = _speckled_rgb()
    out = detail.denoise_sharpen(img, denoise=3, sharpen=0.6)
    assert ImageStat.Stat(out).stddev[0] < ImageStat.Stat(img).stddev[0]


def test_denoise_parameter_changes_the_result():
    from forja.photo import detail
    img = _textured_rgb()
    low = detail.denoise_sharpen(img, denoise=3, sharpen=0.2)
    high = detail.denoise_sharpen(img, denoise=9, sharpen=0.2)
    assert low.tobytes() != high.tobytes()


def test_sharpen_parameter_changes_the_result():
    from forja.photo import detail
    img = _textured_rgb()
    low = detail.denoise_sharpen(img, denoise=3, sharpen=0.2)
    high = detail.denoise_sharpen(img, denoise=3, sharpen=1.0)
    assert low.tobytes() != high.tobytes()
