"""Lint deterministico de HTML/CSS contra tokens carregados da variante
(plano:730,766); `background-image` e `warning`, o resto e `error`."""
from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser

from forja.errors import ForjaError

_HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
_HEX_FULL = re.compile(r"#[0-9A-Fa-f]{6}\Z")
_FONT = re.compile(r"font-family\s*:\s*([^;{}<>]+)", re.I)
_GRADIENT = re.compile(r"(?:linear|radial|conic)-gradient\s*\(", re.I)
_SHADOW = re.compile(r"(?:box-shadow|text-shadow|-webkit-text-stroke|text-stroke)\s*:\s*([^;{}<>]+)", re.I)
_BG_IMAGE = re.compile(r"\bbackground-image\s*:\s*([^;{}<>]+)", re.I)
_BG_URL = re.compile(r"\bbackground\s*:\s*[^;{}<>]*url\(", re.I)
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]")
_IMPORTANT = re.compile(r"\s*!important\s*$", re.I)

_MIN_LOGO_PX = 24  # piso conservador; o plano:730 nao fixa um numero
_MAX_ACCENTS = 2
_DEFAULT_FONTS = frozenset({
    "roboto", "roboto mono", "helvetica neue", "helvetica", "arial", "times",
    "times new roman", "liberation sans", "sans-serif", "serif", "monospace",
    "ui-monospace", "system-ui", "-apple-system", "blinkmacsystemfont"})
_FONT_KEYWORDS = frozenset({"inherit", "initial", "unset", "revert", "revert-layer"})
_EMBLEMS = {
    "lions": ("logos/Emblemas_do_Lions/", "logos/Assinaturas_de_Lions_Clubs_International/",
 "logos/Assinaturas_de_Lions_International/"),
    "leo": ("logos/Emblemas_de_Leos/",),
    "leo-lion": ("logos/Logotipos_de_Leo_a_Leao/", "logos/Logotipos_de_Leo_a_Leão/"),
}
_EMBLEM_MARKERS = tuple(sorted({prefix.split("logos/", 1)[1].rstrip("/")
                                for prefixes in _EMBLEMS.values() for prefix in prefixes}))

def _fail(code, msg, **details):
    return ForjaError(code, msg, details=details or None)

def _issue(level, code, msg, **details):
    return {"level": level, "code": code, "msg": msg, **details}

def _path(value):
    return unicodedata.normalize("NFC", str(value)).replace("\\", "/").lower()

def _strings(value):
    """Achata listas/dicts de configuracao em nomes de texto."""
    if isinstance(value, str):
        return (part.strip() for part in value.split(",") if part.strip())
    items = list(value.values()) if isinstance(value, dict) else value
    if not isinstance(items, (list, tuple, set, frozenset)):
        return iter(())
    return (part for item in items for part in _strings(item))

def _hexes(value):
    if isinstance(value, dict):
        value = value.values()
    elif isinstance(value, str):
        value = [value]
    elif not isinstance(value, (list, tuple, set, frozenset)):
        return []
    out = []
    for item in value:
        if isinstance(item, dict):
            out.extend(_hexes(item))
        elif isinstance(item, str) and _HEX_FULL.fullmatch(item.strip()):
            out.append(item.strip().lower())
    return out

def _palette(tokens, variant):
    if not isinstance(tokens, dict):
        raise _fail("CONFIG_INVALID", "tokens deve ser um dict carregado")
    variants = tokens.get("variants")
    if not isinstance(variants, dict):
        raise _fail("CONFIG_INVALID", "tokens deve ter 'variants' como dict")
    if not isinstance(variant, str) or not variant.strip():
        raise _fail("BRAND_VARIANT_REQUIRED", "variante e obrigatoria")
    if variant not in variants:
        raise _fail("BRAND_VARIANT_REQUIRED", f"variante desconhecida: {variant}",
                    variant=variant, variants=sorted(variants))
    neutrals = set(_hexes(tokens.get("neutrals", [])))
    colors = set(_hexes(variants[variant]))
    return neutrals | colors, colors - neutrals

def _font_allow(fonts):
    names = set(_DEFAULT_FONTS)
    if fonts is not None:
        names.update(_path(name).strip("\"'") for name in _strings(fonts))
    return names

def _font_issues(html, allowed):
    out, seen = [], set()
    for raw in _FONT.findall(html):
        for part in raw.split(","):
            name = _path(_IMPORTANT.sub("", part.strip()).strip("\"'"))
            if not name or name in seen or name.startswith("var("):
                continue
            seen.add(name)
            if name not in _FONT_KEYWORDS and name not in allowed:
                out.append(_issue("error", "BRAND_FONT_UNAUTHORIZED",
                                  f"fonte nao autorizada: {name}", font=name))
    return out

def _logo_prefixes(variant, logos):
    prefixes = list(_EMBLEMS.get(variant, ()))
    prefixes.extend(_strings(logos) if logos is not None else ())
    return tuple(_path(prefix) for prefix in prefixes)

def _color_issues(html, allowed):
    out, seen = [], set()
    for raw in _HEX.findall(html):
        color = raw.lower()
        if color not in allowed and color not in seen:
            seen.add(color)
            out.append(_issue("error", "BRAND_COLOR_INVALID",
                              f"cor fora da paleta da variante: {color}",
                              color=color))
    return out

_VAR_DECL = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*(#[0-9A-Fa-f]{6})\b")
_POS = r"-?\d*\.?\d+(?:%|[a-z]+)?"
_NON_COLOR = re.compile(
    r"(?:from\s+)?-?\d*\.?\d+(?:deg|grad|rad|turn)(?:\s+at\s+.+)?"
    r"|at\s+.+|to\s+(?:left|right|top|bottom|center)"
    r"(?:\s+(?:left|right|top|bottom|center))?"
    rf"|(?:{_POS}\s*)+", re.I)

def _split_args(text):
    """Separa argumentos de topo por virgula, respeitando parenteses."""
    parts, depth, start = [], 0, 0
    for idx, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:idx])
            start = idx + 1
    parts.append(text[start:])
    return parts

def _gradient_args(html):
    """Extrai os argumentos de cada *-gradient(...) do html."""
    out = []
    for match in _GRADIENT.finditer(html):
        depth, end = 0, len(html)
        for idx in range(match.end() - 1, len(html)):
            if html[idx] == "(":
                depth += 1
            elif html[idx] == ")":
                depth -= 1
                if depth == 0:
                    end = idx
                    break
        out.append(_split_args(html[match.end():end]))
    return out

def _gradient_authorized(html, allowed):
    """Todo stop de cor e hex da paleta ou var declarado com hex dela."""
    declared = {name: value.lower() for name, value in _VAR_DECL.findall(html)}
    strip = re.compile(rf"^(?:\s*{_POS})+|(?:\s+{_POS})+$", re.I)
    for args in _gradient_args(html):
        colors = 0
        for raw in args:
            stop = raw.strip()
            if not stop or _NON_COLOR.fullmatch(stop):
                continue
            stop = strip.sub("", stop).strip()
            if not stop:
                continue
            colors += 1
            if _HEX_FULL.fullmatch(stop):
                if stop.lower() not in allowed:
                    return False
                continue
            var = re.fullmatch(r"var\(\s*(--[A-Za-z0-9_-]+)\s*\)", stop)
            if not var or declared.get(var.group(1)) not in allowed:
                return False
        if not colors:
            return False
    return True

def _accent_issues(html, accents, maximum):
    used = sorted({raw.lower() for raw in _HEX.findall(html)} & accents)
    if len(used) <= maximum:
        return []
    return [_issue("error", "BRAND_TOO_MANY_ACCENTS",
                   f"{len(used)} acentos distintos (maximo {maximum})",
                   colors=used)]

class _Images(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "img":
            self.items.append({key.lower(): (value or "")
                               for key, value in attrs})

def _number(value):
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:px)?\s*", value or "", re.I)
    return float(m[1]) if m else None

def _dimension(attrs, prop):
    value = _number(attrs.get(prop, ""))
    if value is None and attrs.get("style"):
        match = re.search(rf"(?:^|;)\s*{prop}\s*:\s*(\d+(?:\.\d+)?)px",
                          attrs["style"], re.I)
        value = float(match.group(1)) if match else None
    return value

def _image_issues(html, variant, prefixes, minimum):
    parser = _Images(); parser.feed(html); parser.close()
    out = []
    for attrs in parser.items:
        src, raw_src = _path(attrs.get("src", "")), attrs.get("src", "")
        if "logos/" not in src and not any(m in src for m in _EMBLEM_MARKERS):
            continue
        if not any(prefix in src for prefix in prefixes):
            out.append(_issue("error", "BRAND_EMBLEM_FORBIDDEN",
                              f"emblema nao permitido na variante {variant}: "
                              f"{raw_src}", variant=variant, src=raw_src))
        small = [f"{prop}={int(value) if value.is_integer() else value}"
                 for prop in ("width", "height")
                 if (value := _dimension(attrs, prop)) is not None
                 and value < minimum]
        if small:
            out.append(_issue("error", "BRAND_LOGO_TOO_SMALL",
                              f"logo abaixo do minimo de {minimum:g} px: "
                              + ", ".join(small), min_px=minimum))
    return out

def _shadow_issues(html):
    out = []
    for raw in _SHADOW.findall(html):
        value = _IMPORTANT.sub("", raw.strip()).strip("\"'").strip()
        if value and value.lower() not in {"none", "initial", "inherit",
                                           "unset", "0"}:
            out.append(_issue("error", "BRAND_DECORATIVE_SHADOW",
                              f"sombra/contorno decorativo: {value}",
                              value=value))
    return out

def _background_issue(html):
    match = _BG_IMAGE.search(html)
    value = match.group(1).strip().strip("\"'") if match else ""
    if (value and value.lower() not in {"none", "initial", "inherit", "unset"}) \
            or _BG_URL.search(html):
        return [_issue("warning", "BRAND_BACKGROUND_IMAGE_REVIEW",
                       "texto sobre background-image exige revisao humana",
                       review="human")]
    return []

def lint_brand(html, tokens, variant, fonts=None, logos=None,
               rules=None) -> list[dict]:
    """Valida HTML/CSS contra a paleta, fontes e emblemas da variante."""
    allowed, accents = _palette(tokens, variant)
    if not isinstance(html, str):
        raise _fail("CONFIG_INVALID", "html deve ser texto")
    rules = rules if isinstance(rules, dict) else {}
    minimum = rules.get("min_logo_px", _MIN_LOGO_PX)
    maximum = rules.get("max_accents", _MAX_ACCENTS)
    if not isinstance(minimum, (int, float)) or isinstance(minimum, bool):
        minimum = _MIN_LOGO_PX
    if not isinstance(maximum, int) or isinstance(maximum, bool):
        maximum = _MAX_ACCENTS
    issues = []
    issues.extend(_color_issues(html, allowed))
    issues.extend(_font_issues(html, _font_allow(fonts)))
    issues.extend(_image_issues(html, variant, _logo_prefixes(variant, logos),
                                minimum))
    emoji = _EMOJI.search(html)
    if emoji:
        issues.append(_issue("error", "BRAND_EMOJI_ICON",
                             f"emoji como icone: {emoji.group(0)}",
                             char=emoji.group(0)))
    if _GRADIENT.search(html) and (
            rules.get("allow_brand_gradient") is not True
            or not _gradient_authorized(html, allowed)):
        issues.append(_issue("error", "BRAND_GENERIC_GRADIENT",
                             "gradiente generico nao autorizado"))
    issues.extend(_accent_issues(html, accents, maximum))
    issues.extend(_shadow_issues(html))
    issues.extend(_background_issue(html))
    return issues
