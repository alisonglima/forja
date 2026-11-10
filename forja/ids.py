"""Ids de cue/cena: seguros para virar nome de arquivo dentro do projeto."""
from __future__ import annotations

import re

from .errors import ForjaError

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def is_safe_id(value) -> bool:
    """Verdadeiro para ids que nao saem do diretorio (sem /, \\ ou ..)."""
    return (
        isinstance(value, str)
        and bool(_ID_RE.match(value))
        and ".." not in value
    )


def require_safe_id(value, what="id") -> str:
    if not is_safe_id(value):
        raise ForjaError(
            "CONFIG_INVALID",
            "%s invalido: %r" % (what, value),
            hint="use letras, numeros, ponto, hifen ou sublinhado (sem barra e sem ..)",
        )
    return str(value)
