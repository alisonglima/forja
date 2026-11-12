"""Promocao e verificacao de templates aprovados no Open Design.

Copia para `brands/<id>/templates/` e grava o sha256 no `manifest.json`;
hash divergente e `TEMPLATE_HASH_MISMATCH` exit 1 (plano:430,477,1377).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from forja.errors import ForjaError

SCHEMA = 1
MANIFEST = "manifest.json"
VARIANTS = ("lions", "leo", "leo-lion")  # lista oficial do DS (plano:2048)
_LEGACY = ("node_modules", ".od-skills", ".cache")
_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
_HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
_VARIANT = re.compile(r"\bdata-variant\s*=\s*(?:\"([^\"]+)\"|'([^']+)')", re.I)
_CHUNK = 1024 * 1024

def _fail(code, msg, **details):
    return ForjaError(code, msg, details=details or None)

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()

def _read_html(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise _fail("CONFIG_INVALID", "template ilegivel: %s" % path,
                    path=str(path)) from exc

def _check_html(html: str, path=None) -> None:
    """Exige `data-variant` e nenhum hex cru no template."""
    match = _VARIANT.search(html)
    if match is None or not (match.group(1) or match.group(2) or "").strip():
        raise _fail("CONFIG_INVALID", "template sem data-variant: %s" % path,
                    path=str(path) if path else None)
    hexes = sorted({raw.lower() for raw in _HEX.findall(html)})
    if hexes:
        raise _fail("CONFIG_INVALID",
                    "template com cor crua (%s); use var(--...)" % hexes[0],
                    path=str(path) if path else None, colors=hexes)

def _piece(piece) -> str:
    if not isinstance(piece, str) or not piece.strip():
        raise _fail("CONFIG_INVALID", "nome do template deve ser texto nao vazio")
    if not _SLUG.fullmatch(piece):
        raise _fail("CONFIG_INVALID", "nome do template invalido: %r" % piece,
                    template=piece)
    return piece

def _source(src) -> Path:
    path = Path(src)
    try:
        resolved = path.resolve()
    except OSError as exc:
        raise _fail("MISSING_INPUT", "template ausente: %s" % path,
                    path=str(path)) from exc
    if any(part in _LEGACY for part in (*path.parts, *resolved.parts)):
        raise _fail("CONFIG_INVALID", "template nao pode vir de cache: %s" % path,
                    path=str(path))
    if not resolved.is_file():
        raise _fail("MISSING_INPUT", "template ausente: %s" % path,
                    path=str(path))
    return resolved

def _load_manifest(path: Path, brand: str) -> dict:
    if not path.is_file():
        return {"schema": SCHEMA, "brand": brand,
                "variants": list(VARIANTS), "templates": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _fail("CONFIG_INVALID", "manifesto de template ilegivel: %s" % path,
                    path=str(path)) from exc
    if not isinstance(data, dict) or not isinstance(data.get("templates"), dict):
        raise _fail("CONFIG_INVALID",
                    "manifesto de template deve ter 'templates' como objeto",
                    path=str(path))
    data.setdefault("schema", SCHEMA)
    data.setdefault("brand", brand)
    data.setdefault("variants", list(VARIANTS))
    return data

def _record(piece: str, sha: str, *, approved_by, approved_at, od_project,
            od_artifact, design_system, preset) -> dict:
    if not all(isinstance(value, str) and value.strip()
               for value in (approved_by, approved_at, od_project, od_artifact,
                             design_system, preset)):
        raise _fail("CONFIG_INVALID",
                    "metadados da promocao devem ser texto nao vazio",
                    template=piece)
    return {"file": piece + ".html", "sha256": sha,
            "approved_by": approved_by, "approved_at": approved_at,
            "od_project": od_project, "od_artifact": od_artifact,
            "design_system": design_system, "preset": preset}

def promote_template(src, brand, piece, *, approve_hash, approved_by,
                     od_project, od_artifact, design_system, preset, now,
                     force=False) -> dict:
    """Copia o template aprovado e grava a entrada com sha256 no manifesto."""
    piece = _piece(piece)
    source = _source(src)
    _check_html(_read_html(source), source)
    actual = _sha256(source)
    if approve_hash != actual:
        raise _fail("TEMPLATE_HASH_MISMATCH",
                    "hash aprovado nao confere com o template: %s" % source,
                    expected=approve_hash, actual=actual, template=piece)
    base = Path(brand)
    templates = base / "templates"
    dest = templates / (piece + ".html")
    try:
        dest.parent.resolve().relative_to(templates.resolve())
    except (OSError, ValueError) as exc:
        raise _fail("CONFIG_INVALID", "destino fora de templates/: %r" % piece,
                    template=piece) from exc
    if dest.exists() and not force:
        raise _fail("APPROVAL_STALE",
                    "template ja aprovado; use --force com novo --approve-hash",
                    template=piece, path=str(dest))
    entry = _record(piece, actual, approved_by=approved_by, approved_at=now,
                    od_project=od_project, od_artifact=od_artifact,
                    design_system=design_system, preset=preset)
    templates.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(source.read_bytes())
    entry["sha256"] = _sha256(dest)
    manifest_path = templates / MANIFEST
    manifest = _load_manifest(manifest_path, base.name)
    manifest["variants"] = list(VARIANTS)
    manifest["templates"][piece] = entry
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return entry

def verify_template(brand, piece) -> dict:
    """Confere o sha256 do template promovido contra o manifesto."""
    piece = _piece(piece)
    base = Path(brand)
    templates = base / "templates"
    dest = templates / (piece + ".html")
    manifest_path = templates / MANIFEST
    if not dest.is_file() or not manifest_path.is_file():
        raise _fail("MISSING_PREREQ", "template promovido ausente: %s" % dest,
                    brand=base.name, template=piece, path=str(dest))
    manifest = _load_manifest(manifest_path, base.name)
    entry = manifest["templates"].get(piece)
    if not isinstance(entry, dict) or not entry.get("sha256"):
        raise _fail("MISSING_PREREQ",
                    "template sem entrada no manifesto: %s" % piece,
                    brand=base.name, template=piece)
    actual = _sha256(dest)
    if entry["sha256"] != actual:
        raise _fail("TEMPLATE_HASH_MISMATCH",
                    "template mudou fora do OD: %s" % piece,
                    brand=base.name, template=piece,
                    expected=entry["sha256"], actual=actual)
    _check_html(_read_html(dest), dest)
    return entry
