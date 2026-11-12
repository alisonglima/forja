"""Passo `inspect` do workflow post: dimensoes, contraste e dedup."""
from __future__ import annotations

import datetime
import json
from pathlib import Path

from .. import dedup, formats, qa_geometry, qa_visual
from ..errors import ForjaError

_ALIASES = {"ig-square": "ig-feed-quadrado", "ig-portrait": "ig-feed-4x5",
            "story": "ig-story"}
_GATE_CODES = ("CONTRAST_PHOTO", "DUPLICATE_ARTIFACT")
_SUFFIXES = (".png", ".jpg", ".jpeg", ".pdf")

def _fail(code, msg, **details) -> ForjaError:
    return ForjaError(code, msg, details=details or None)

def _piece(ctx) -> str:
    piece = (ctx.cfg or {}).get("piece")
    if not isinstance(piece, str) or not piece.strip():
        raise _fail("MISSING_INPUT", "config sem a peca do post")
    return piece.strip()

def _load(path, label: str) -> dict:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise _fail("MISSING_INPUT", "%s ausente ou ilegivel: %s" % (label, path),
                    path=str(path)) from exc
    except ValueError as exc:
        raise _fail("CONFIG_INVALID", "%s com JSON invalido: %s" % (label, path),
                    path=str(path)) from exc
    if not isinstance(data, dict):
        raise _fail("CONFIG_INVALID", "%s deve ser um objeto JSON" % label,
                    path=str(path))
    return data

def _lint(ctx, piece: str) -> dict:
    """Le o lint; relatorio reprovado ou ausente barra o inspect."""
    path = Path(ctx.work) / "lint" / (piece + ".json")
    if not path.is_file():
        raise _fail("GATE_FAILED",
                    "lint ausente: rode o passo lint antes do inspect",
                    path=str(path))
    data = _load(path, "lint")
    errors = data.get("errors", 0)
    if data.get("ok") is False or errors:
        raise _fail("GATE_FAILED", "lint reprovado: %s erro(s)" % errors,
                    path=str(path), errors=data.get("issues") or [])
    return data

def _artifact(ctx, piece: str) -> Path:
    for suffix in _SUFFIXES:
        path = Path(ctx.work) / "render" / (piece + suffix)
        if path.is_file():
            return path
    raise _fail("ASSET_MISSING", "arte renderizada ausente para %r" % piece,
                path=str(Path(ctx.work) / "render" / (piece + ".png")))

def _row(ctx, lint: dict):
    """Linha da matriz de formatos, se o config ou o lint declararem o formato."""
    for value in ((ctx.cfg or {}).get("format"), lint.get("format"),
                  lint.get("formato")):
        if isinstance(value, str) and value.strip():
            try:
                return formats.get(_ALIASES.get(value.strip(), value.strip()))
            except ForjaError:
                return None
    return None

def _expected(ctx, lint: dict):
    """Dimensoes esperadas; sem formato declarado nao inventa canvas."""
    row = _row(ctx, lint)
    if row is not None:
        return int(row["largura"]), int(row["altura"])
    dims = lint.get("dimensoes")
    dims = dims if isinstance(dims, dict) else lint
    for wkey, hkey in (("width", "height"), ("largura", "altura")):
        width, height = dims.get(wkey), dims.get(hkey)
        if all(isinstance(v, int) and not isinstance(v, bool)
               for v in (width, height)):
            return width, height
    return None

def _hashes(ctx) -> list:
    """Entradas do registro de dedup; registro ilegivel falha fechado."""
    path = Path(ctx.work) / "hashes.json"
    if not path.is_file():
        return []
    data = _load(path, "registro de hashes")
    entries = data.get("entries", data)
    if not isinstance(entries, list):
        raise _fail("CONFIG_INVALID", "work/hashes.json deve listar as entradas",
                    path=str(path))
    return [entry for entry in entries if isinstance(entry, dict)]

def _raise_issue(target: Path, result: dict) -> None:
    issue = next((item for item in result.get("issues") or []
                  if item.get("level") == "error"), None)
    if issue is None:
        return
    code = issue.get("code")
    raise _fail(code if code in _GATE_CODES else "GATE_FAILED",
                str(issue.get("msg") or "inspect reprovado"),
                path=str(target), sha256=result.get("sha256"),
                issues=result.get("issues") or [])

def run_inspect(ctx) -> dict:
    """Inspeciona a arte renderizada e grava `work/inspect/<peca>.json`."""
    piece = _piece(ctx)
    lint = _lint(ctx, piece)
    target = _artifact(ctx, piece)
    expected = _expected(ctx, lint)
    measured = qa_geometry.measure(target)
    if expected is None and measured is not None:
        expected = (measured["width"], measured["height"])
    values = lint.get("contrast", lint.get("contraste"))
    contrast = list(values) if isinstance(values, list) else []
    now = (ctx.cfg or {}).get("now")
    now = datetime.datetime.fromisoformat(now) if isinstance(now, str) else now
    hashes = [e for e in _hashes(ctx) if Path(str(e.get("path") or "")).name != target.name]
    result = qa_visual.inspect_artifact(
        target, expected or (0, 0),
        brand_id=(ctx.cfg or {}).get("brand_id", ""),
        hashes=hashes, contrast=contrast, now=now)
    _raise_issue(target, result)
    payload = {
        "schema": 1, "ok": True, "piece": piece,
        "brand_id": (ctx.cfg or {}).get("brand_id", ""),
        "artifact": target.relative_to(ctx.root).as_posix(),
        "width": result["width"], "height": result["height"],
        "bytes": measured["bytes"] if measured else target.stat().st_size,
        "sha256": result["sha256"], "contrast": contrast,
        "issues": result.get("issues") or [],
    }
    path = Path(ctx.work) / "inspect" / (piece + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(path)
    dedup.record(ctx.root, target, scope=(ctx.cfg or {}).get("brand_id", ""),
                 piece=piece, now=now)
    return {"ok": True, "path": path.relative_to(ctx.root).as_posix(),
            "sha256": result["sha256"], "width": result["width"],
            "height": result["height"]}
