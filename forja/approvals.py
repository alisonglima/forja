"""Hash deterministico de brief e pacote aprovado (N-03)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import yaml

from .errors import ForjaError
from .ids import require_safe_id

APPROVAL_VERSION = 2

_CHUNK = 1024 * 1024


def _canonical(value) -> str:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(_CHUNK):
            digest.update(block)
    return digest.hexdigest()


def _digest(parts) -> str:
    digest = hashlib.sha256()
    for label, value in parts:
        digest.update(label.encode("utf-8") + b"\0")
        digest.update(value.encode("utf-8") + b"\0")
    return digest.hexdigest()


def _read_brief(root: Path) -> dict:
    path = root / "brief.yaml"
    if not path.is_file():
        raise ForjaError(
            "MISSING_INPUT",
            "brief.yaml ausente: sem brief nao ha o que aprovar",
            hint="rode `forja init` ou restaure o brief.yaml",
        )
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ForjaError("CONFIG_INVALID", "brief.yaml ilegivel: %s" % exc) from exc
    if not isinstance(data, dict) or not data:
        raise ForjaError("CONFIG_INVALID", "brief.yaml deve ser um mapeamento nao vazio")
    return data


def _fields(data: dict) -> tuple[str, str, str]:
    values = []
    for key in ("piece", "brand_id", "format"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ForjaError("CONFIG_INVALID", "brief.%s deve ser texto nao vazio" % key)
        values.append(value)
    return values[0], require_safe_id(values[1], "brief.brand_id"), values[2]


def _read_manifest(root: Path, brand: str) -> dict:
    path = root / "brands" / brand / "manifest.json"
    if not path.is_file():
        raise ForjaError(
            "MISSING_INPUT",
            "manifest da marca ausente: %s" % path.relative_to(root).as_posix(),
            hint="restaure brands/<id>/manifest.json antes de aprovar",
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ForjaError("CONFIG_INVALID", "manifest da marca ilegivel: %s" % exc) from exc
    if not isinstance(data, dict) or not data:
        raise ForjaError("CONFIG_INVALID", "manifest da marca deve ser um objeto nao vazio")
    return data


def hash_brief(root) -> str:
    """sha256 de brief.yaml normalizado + manifest da marca + campos da peca."""
    root = Path(root)
    brief = _read_brief(root)
    piece, brand, fmt = _fields(brief)
    manifest = _read_manifest(root, brand)
    return _digest(
        [
            ("brief", _canonical(brief)),
            ("manifest", _canonical(manifest)),
            ("piece", piece),
            ("brand_id", brand),
            ("format", fmt),
        ]
    )


def _record(path: Path, label: str) -> dict:
    return {"path": label, "size": path.stat().st_size, "sha256": _sha256_file(path)}


def hash_files(paths, extra=None) -> str:
    """sha256 de (caminho relativo, tamanho, conteudo) ordenado, mais ``extra``."""
    raw = [Path(p) for p in paths]
    resolved = [p.resolve() for p in raw]
    try:
        base = Path(os.path.commonpath([str(p.parent) for p in resolved]))
        labels = [p.relative_to(base).as_posix() for p in resolved]
    except (ValueError, OSError):
        labels = [p.name for p in resolved]
    records = []
    for path, label in zip(raw, labels):
        if not path.is_file():
            raise ForjaError("MISSING_INPUT", "arquivo ausente para hash: %s" % label)
        records.append(_record(path, label))
    records.sort(key=_canonical)
    return _digest([("files", _canonical(records)), ("extra", _canonical(extra))])


def hash_piece(root) -> str:
    """hash_brief + cada artefato de out/ (relpath, tamanho, sha256), ordenado."""
    root = Path(root)
    base = hash_brief(root)
    records = []
    out = root / "out"
    if out.is_dir():
        records = [
            _record(path, path.relative_to(root).as_posix())
            for path in out.rglob("*")
            if path.is_file()
        ]
    records.sort(key=_canonical)
    return _digest([("brief", base), ("artifacts", _canonical(records))])
