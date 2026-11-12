"""Tokens do design system -> `brand` do video (plano:1449,1574).

Le `design-tokens.json`, seleciona `variant:<variante>` com fallback `base` e valida hex, tipos e contraste tinta/papel de 4.5:1.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from forja.errors import ForjaError

_HEX = re.compile(r"#[0-9A-Fa-f]{6}\Z")
_KEYS = ("primary", "ink", "paper", "accent", "font", "safe_margin")
_TYPES = {"primary": "color", "ink": "color", "paper": "color",
          "accent": "color", "font": "font", "safe_margin": "dimension"}
_ALIASES = {key: key for key in _KEYS}
_ALIASES.update({"--primary": "primary", "--fg": "ink", "--ink": "ink",
                 "--bg": "paper", "--paper": "paper", "--accent": "accent",
                 "--font-display": "font", "--safe": "safe_margin"})

def _fail(code, msg, **details):
    return ForjaError(code, msg, details=details or None)


def _color(value, key):
    text = value.strip() if isinstance(value, str) else ""
    if not _HEX.fullmatch(text):
        raise _fail("CONFIG_INVALID", f"{key} deve ser hex #RRGGBB",
                    token=key, value=repr(value))
    return text


def _margin(value, key):
    text = value.strip() if isinstance(value, str) else value
    text = text[:-2].strip() if isinstance(text, str) and text.endswith("px") else text
    try:
        number = math.nan if isinstance(text, bool) else float(text)
    except (TypeError, ValueError):
        number = math.nan
    if not (0 <= number <= 240):
        raise _fail("CONFIG_INVALID", f"{key} deve ser numero de 0 a 240",
                    token=key, value=repr(value))
    return int(number) if number.is_integer() else number


def _luminance(color):
    channels = [int(color[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
              for c in channels]
    return sum(w * c for w, c in zip((0.2126, 0.7152, 0.0722), linear))


def _ratio(color_a, color_b):
    high, low = sorted((_luminance(color_a), _luminance(color_b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def load_brand(path, variant) -> dict:
    """Carrega `design-tokens.json` e devolve o `brand` da variante."""
    if variant is not None and (not isinstance(variant, str) or not variant.strip()):
        raise _fail("CONFIG_INVALID", "variante deve ser texto nao vazio")
    token_path = Path(path)
    if ".." in token_path.parts:
        raise _fail("CONFIG_INVALID", "caminho de tokens nao pode conter '..'",
                    path=str(token_path))
    if not token_path.is_file():
        raise _fail("MISSING_INPUT", f"design-tokens.json nao encontrado: {token_path}",
                    path=str(token_path))
    try:
        doc = json.loads(token_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _fail("CONFIG_INVALID", f"design-tokens.json invalido: {token_path}",
                    path=str(token_path)) from exc
    tokens = doc.get("tokens") if isinstance(doc, dict) else None
    if not isinstance(tokens, list) or not tokens:
        raise _fail("CONFIG_INVALID",
                    "design-tokens.json deve ter 'tokens' como lista nao vazia")
    known = {token["layer"][8:] for token in tokens if isinstance(token, dict)
             and str(token.get("layer", "")).startswith("variant:")}
    if variant and known and variant not in known:
        raise _fail("BRAND_VARIANT_REQUIRED", f"variante desconhecida: {variant}",
                    variant=variant, variants=sorted(known))
    layers = {"base"} | ({f"variant:{variant}"} if variant else set())
    brand = {}
    for token in tokens:
        if not isinstance(token, dict):
            raise _fail("CONFIG_INVALID", "cada token deve ser um objeto")
        name = token.get("name")
        key = _ALIASES.get(name) if isinstance(name, str) else None
        if key is None or token.get("layer") not in layers:
            continue
        expected = _TYPES[key]
        if token.get("type") != expected:
            raise _fail("CONFIG_INVALID",
                        f"token {name!r} deve ter type {expected!r}",
                        token=name, type=repr(token.get("type")))
        value = token.get("value")
        if key == "font":
            if not isinstance(value, str) or not value.strip():
                raise _fail("CONFIG_INVALID", "font deve ser texto nao vazio",
                            token=key, value=repr(value))
            brand[key] = value.strip()
        elif key == "safe_margin":
            brand[key] = _margin(value, key)
        else:
            brand[key] = _color(value, key)
    if "primary" not in brand and "accent" in brand:
        brand["primary"] = brand["accent"]
    missing = [key for key in _KEYS if key not in brand]
    if missing:
        raise _fail("CONFIG_INVALID", "tokens de marca ausentes: " + ", ".join(missing),
                    missing=missing)
    ratio = _ratio(brand["ink"], brand["paper"])
    if ratio < 4.5:
        raise _fail("GATE_FAILED",
                    f"contraste tinta/papel {ratio:.2f}:1 abaixo de 4.5:1",
                    ratio=round(ratio, 2))
    return {key: brand[key] for key in _KEYS}
