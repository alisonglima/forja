from __future__ import annotations

from PIL import Image

from forja.errors import ForjaError


def _rgb(color) -> tuple[int, int, int]:
    """Interpreta `#RRGGBB` (caixa indiferente) como tupla RGB."""
    if not isinstance(color, str) or len(color) != 7 or color[0] != "#":
        raise ForjaError("USAGE", f"cor invalida: {color!r}", hint="use hex #RRGGBB")
    try:
        return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
    except ValueError as exc:
        raise ForjaError(
            "USAGE", f"cor invalida: {color!r}", hint="use hex #RRGGBB"
        ) from exc


def duotone(img: Image.Image, dark: str, light: str) -> Image.Image:
    """Mapeia a luminancia da imagem para o gradiente `dark` -> `light`."""
    dark_rgb, light_rgb = _rgb(dark), _rgb(light)
    lum = img.convert("L")
    out = Image.new("RGB", lum.size)
    out.putdata(
        [
            tuple(
                round(d + (l - d) * value / 255)
                for d, l in zip(dark_rgb, light_rgb)
            )
            for value in lum.getdata()
        ]
    )
    return out


def blend(img: Image.Image, overlay: Image.Image, alpha: float = 0.5) -> Image.Image:
    """Compõe `overlay` sobre `img` com peso `alpha` (0 = base, 1 = overlay)."""
    base = img.convert("RGB")
    top = overlay.convert("RGB")
    out = Image.new("RGB", base.size)
    out.putdata(
        [
            tuple(round(b + (o - b) * alpha) for b, o in zip(base_px, top_px))
            for base_px, top_px in zip(base.getdata(), top.getdata())
        ]
    )
    return out
