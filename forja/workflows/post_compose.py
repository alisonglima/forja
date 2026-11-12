"""Passos `template` e `compose` do workflow `post` (L-POST-COMPOSE-01)."""
from __future__ import annotations

import hashlib
import json
import re
from html import escape
from pathlib import Path

from .. import formats, templates
from ..errors import ForjaError

# Presets canonicos do kit que nao usam o mesmo id da matriz de formatos.
_ALIASES = {
    "ig-square": "ig-feed-quadrado",
    "ig-portrait": "ig-feed-4x5",
    "story": "ig-story",
}
_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*\Z")


def _fail(code, msg, **details):
    raise ForjaError(code, msg, details=details or None)


def _names(cfg):
    brand, piece = cfg.get("brand_id"), cfg.get("piece")
    for label, value in (("brand_id", brand), ("piece", piece)):
        if not isinstance(value, str) or not _SLUG.fullmatch(value.strip()):
            _fail("CONFIG_INVALID", "%s invalido: %r" % (label, value))
    return brand.strip(), piece.strip()


def _read_json(path, code="MISSING_INPUT"):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError:
        _fail(code, "entrada ausente ou ilegivel: %s" % path, path=str(path))
    except ValueError:
        _fail("CONFIG_INVALID", "JSON invalido: %s" % path, path=str(path))


def _find_asset(ref, assets):
    path = Path(ref)
    if path.is_absolute() or ".." in path.parts:
        _fail("ASSET_MISSING", "ativo fora de work/assets: %r" % ref,
              arquivo=ref)
    for item in assets:
        if not isinstance(item, dict):
            continue
        for key in ("id", "arquivo", "path"):
            value = item.get(key)
            if isinstance(value, str) and value and (
                    value == ref or Path(value).name == path.name):
                return item
    _fail("ASSET_MISSING", "ativo citado no copy nao esta em work/assets.json: %r"
          % ref, arquivo=ref)


def _check_assets(copy, assets):
    refs = []
    for key in ("imagem", "foto"):
        value = copy.get(key)
        if isinstance(value, str) and value.strip():
            refs.append(value)
    values = copy.get("imagens")
    if isinstance(values, list):
        refs.extend(v for v in values if isinstance(v, str) and v.strip())
    for ref in refs:
        _find_asset(ref, assets)


def _fill(html, copy):
    values = {key: copy.get(key, "")
              for key in ("titulo", "corpo", "cta", "legenda", "alt")}
    tags = copy.get("hashtags")
    if isinstance(tags, list):
        values["hashtags"] = " ".join(str(tag) for tag in tags
                                      if str(tag).strip())
    for key, value in values.items():
        html = html.replace("{{%s}}" % key, escape(str(value), quote=True))
    return html


def run_template(ctx):
    """Verifica o template promovido e grava o hash em `work/template.json`."""
    brand, piece = _names(ctx.cfg or {})
    root = Path(ctx.root)
    entry = templates.verify_template(root / "brands" / brand, piece)
    data = {"schema": 1, "brand": brand, "template": piece,
            "file": entry.get("file") or piece + ".html",
            "sha256": entry.get("sha256"), "preset": entry.get("preset"),
            "path": "brands/%s/templates/%s.html" % (brand, piece)}
    target = Path(ctx.work) / "template.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    return {"ok": True, **data}


def run_compose(ctx):
    """Preenche o template verificado e grava `work/compose/<peca>.html`."""
    cfg = ctx.cfg or {}
    brand, piece = _names(cfg)
    format_id = cfg.get("format")
    if not isinstance(format_id, str) or not format_id.strip():
        _fail("FORMAT_UNSUPPORTED", "formato ausente: %r" % (format_id,))
    format_id = format_id.strip()
    row = formats.get(_ALIASES.get(format_id, format_id))
    root = Path(ctx.root)
    out_path = Path(ctx.work) / "compose" / (piece + ".html")
    copy = _read_json(Path(ctx.work) / "copy.json")
    if not isinstance(copy, dict):
        _fail("CONFIG_INVALID", "copy.json deve ser um objeto")
    assets_path = Path(ctx.work) / "assets.json"
    data = _read_json(assets_path) if assets_path.is_file() else {"assets": []}
    if not isinstance(data, dict) or not isinstance(data.get("assets"), list):
        _fail("CONFIG_INVALID", "assets.json deve ter 'assets' como lista")
    _check_assets(copy, data["assets"])
    entry = templates.verify_template(root / "brands" / brand, piece)
    source = root / "brands" / brand / "templates" / (
        entry.get("file") or piece + ".html")
    try:
        html = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        _fail("MISSING_PREREQ", "template promovido ilegivel: %s" % source,
              path=str(source))
    html = _fill(html, copy)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
    return {"ok": True, "piece": piece, "format": format_id,
            "width": row["largura"], "height": row["altura"],
            "path": out_path.relative_to(root).as_posix(), "sha256": digest}
