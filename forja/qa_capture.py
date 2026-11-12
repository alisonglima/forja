"""Capturas de QA em 360/1280 px e marcadores de inspecao humana."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from PIL import Image

from forja.errors import ForjaError

_INSPECT = Path("work") / "inspect"
_REVIEW = Path("work") / "review"


def _safe_piece(piece) -> str:
    """Nome de peca e um unico componente de caminho, sem escapar de work/."""
    name = str(piece or "")
    if (not name or name in (".", "..") or "/" in name
            or "\\" in name or "\x00" in name):
        raise ForjaError("USAGE", f"peca invalida: {piece!r}",
                         hint="use so o nome da peca, sem caminho")
    return name


def _resize(src, width: int) -> Image.Image:
    """Le e redimensiona mantendo a proporcao; falha antes de criar saida."""
    path = Path(src)
    if not path.is_file():
        raise ForjaError("MISSING_INPUT", f"captura de origem ausente: {path}",
                         hint="gere o PNG da peca antes de capturar")
    try:
        with Image.open(path) as image:
            image.load()
            height = max(1, round(image.height * width / image.width))
            return image.convert("RGB").resize(
                (width, height), Image.Resampling.LANCZOS)
    except (OSError, ValueError) as exc:
        raise ForjaError("GATE_FAILED", f"PNG invalido para captura: {path}",
                         details={"error": str(exc)}) from exc


def _save(image: Image.Image, dest: Path) -> Path:
    """Grava o PNG de forma atomica, sem deixar arquivo parcial."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{dest.name}.", suffix=".png", dir=dest.parent)
    os.close(fd)
    try:
        image.save(temporary, format="PNG")
        os.replace(temporary, dest)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return dest


def _capture(src, root, piece, width: int) -> Path:
    name = _safe_piece(piece)
    image = _resize(src, width)
    return _save(image, Path(root) / _INSPECT / f"{name}-{width}.png")


def capture_360(src, root, piece) -> Path:
    """Grava `work/inspect/<peca>-360.png` com 360 px de largura."""
    return _capture(src, root, piece, 360)


def capture_1280(src, root, piece) -> Path:
    """Grava `work/inspect/<peca>-1280.png` com 1280 px de largura."""
    return _capture(src, root, piece, 1280)


def record_open(root, piece, width: int, *, by, at, sha256, seen) -> Path:
    """Grava o marcador `work/review/<peca>.<width>.aberta`."""
    name = _safe_piece(piece)
    if width not in (360, 1280):
        raise ForjaError("USAGE", f"captura deve ser 360 ou 1280: {width!r}",
                         hint="abra as capturas de 360 px e de 1280 px")
    text = "\n".join([
        f"peca: {name}",
        f"captura: {width}px",
        f"by: {by}",
        f"at: {at}",
        f"sha256: {sha256}",
        f"seen: {seen}",
        "",
    ])
    review = Path(root) / _REVIEW
    dest = review / f"{name}.{width}.aberta"
    review.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return dest
