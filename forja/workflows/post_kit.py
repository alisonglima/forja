"""Passos `render` e `lint` do workflow post: kit fixo e portao de qualidade."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from .. import kit
from ..errors import ForjaError

_PDF_FORMATS = {"a4", "a5", "pdf-a4-a5"}


def _fail(code, msg, **details) -> ForjaError:
    return ForjaError(code, msg, details=details or None)


def _write_json(path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _piece(ctx) -> str:
    piece = (ctx.cfg or {}).get("piece")
    if not isinstance(piece, str) or not piece.strip():
        raise _fail("MISSING_INPUT", "config sem a peca do post")
    return piece.strip()


def _suffix(ctx) -> str:
    fmt = str((ctx.cfg or {}).get("format") or "png").strip().lower()
    if fmt in _PDF_FORMATS or "pdf" in fmt:
        return ".pdf"
    if "jpeg" in fmt or "jpg" in fmt:
        return ".jpg"
    return ".png"


def _source_path(ctx, piece: str) -> Path:
    return Path(ctx.work) / "compose" / (piece + ".html")


def _render_target(ctx, piece: str) -> Path:
    return Path(ctx.work) / "render" / (piece + _suffix(ctx))


def _promote(result, target: Path, root) -> None:
    """Move a saida impressa pelo kit para `work/render/<peca>`."""
    if target.is_file():
        return
    for item in result.get("outputs") or []:
        source = Path(item)
        if not source.is_absolute():
            source = Path(root) / source
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            return
    raise _fail(
        "PROVIDER_ERROR",
        "kit export nao gerou o arquivo esperado",
        output=str(target),
    )


def run_render(ctx, *, run=subprocess.run) -> dict:
    """Renderiza o HTML composto com o kit fixo e grava work/render/<peca>."""
    piece = _piece(ctx)
    source = _source_path(ctx, piece)
    if not source.is_file():
        raise _fail(
            "MISSING_INPUT",
            "HTML composto ausente: rode o passo compose antes do render",
            path=str(source),
        )
    target = _render_target(ctx, piece)
    result = kit.export(str(source), run=run, cwd=str(ctx.root))
    _promote(result, target, ctx.root)
    return {"ok": True, "output": str(target), "cmd": result.get("cmd")}


def _static_issues(path: Path) -> list[dict]:
    """Preflight local: o card fixo e o contrato minimo do template."""
    html = path.read_text(encoding="utf-8")
    if "[data-od-card]" in html or "data-od-card" in html:
        return []
    return [{
        "level": "error",
        "code": "CARD_MISSING",
        "file": path.name,
        "msg": "HTML composto sem [data-od-card]",
    }]


def run_lint(ctx, *, run=subprocess.run) -> dict:
    """Roda o preflight do kit e reprova com GATE_FAILED quando ha erro."""
    piece = _piece(ctx)
    source = _source_path(ctx, piece)
    if not source.is_file():
        raise _fail(
            "MISSING_INPUT",
            "HTML composto ausente: rode o passo compose antes do lint",
            path=str(source),
        )
    issues = _static_issues(source)
    if not issues:
        try:
            checked = kit.check(str(source), run=run, cwd=str(ctx.root))
        except ForjaError as exc:
            if exc.code != "GATE_FAILED":
                raise
            issues = list((exc.details or {}).get("issues") or [])
        else:
            issues = list(checked.get("issues") or [])
    errors = [i for i in issues if i.get("level") == "error"]
    warnings = [i for i in issues if i.get("level") != "error"]
    path = Path(ctx.work) / "lint" / (piece + ".json")
    _write_json(path, {
        "ok": not errors,
        "errors": len(errors),
        "warnings": len(warnings),
        "issues": issues,
        "html_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "screenshots": [],
    })
    if errors:
        raise _fail(
            "GATE_FAILED",
            "lint reprovou com %d erro(s)" % len(errors),
            path=str(path),
            issues=errors,
        )
    return {"ok": True, "errors": 0, "warnings": len(warnings), "path": str(path)}
