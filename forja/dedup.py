"""Deduplicacao de arte por conteudo (sha256) e similaridade perceptual (dHash)."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from PIL import Image

_CHUNK = 1024 * 1024
_REGISTRY = Path("work") / "hashes.json"
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_HASHTAG = re.compile(r"#\w+")


def content_hash(path) -> str:
    """sha256 do conteudo em streaming; arquivo ausente propaga OSError."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def text_hash(text) -> str:
    """sha256 da legenda normalizada (caixa, URL/hashtag e espacos)."""
    normalized = _HASHTAG.sub(" ", _URL.sub(" ", str(text).lower()))
    return hashlib.sha256(" ".join(normalized.split()).encode("utf-8")).hexdigest()


def perceptual_hash(path) -> str:
    """dHash de 64 bits (imagem 9x8 em tons de cinza)."""
    with Image.open(path) as image:
        pixels = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS).tobytes()
    bits = 0
    for y in range(8):
        row = y * 9
        for x in range(8):
            bits = (bits << 1) | int(pixels[row + x] < pixels[row + x + 1])
    return f"{bits:016x}"


def _now(value):
    value = value or datetime.datetime.now(datetime.timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)


def _load(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("entries", [])
    if not isinstance(data, list):
        raise ValueError("registro de hashes invalido")
    return [item for item in data if isinstance(item, dict)]


def _write(path: Path, entries: list[dict]) -> None:
    """Grava o registro atomicamente (temporario no mesmo diretorio)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "entries": entries}, fh,
                      ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _is_recent(entry: dict, now: datetime.datetime, days: int) -> bool:
    raw = entry.get("at")
    if not isinstance(raw, str):
        return False
    try:
        at = datetime.datetime.fromisoformat(raw)
    except ValueError: return False
    if at.tzinfo is None:
        at = at.replace(tzinfo=datetime.timezone.utc)
    return now - at <= datetime.timedelta(days=days)


def _relative(root, path) -> str:
    return Path(os.path.relpath(Path(path).resolve(), Path(root).resolve())).as_posix()

def record(root, path, *, scope="", piece=None, now=None, days=30, registry_path=None) -> dict:
    """Grava a arte no registro e poda entradas fora da janela de ``days``."""
    at = _now(now)
    target = Path(registry_path) if registry_path is not None else Path(root) / _REGISTRY
    entries = [item for item in _load(target) if _is_recent(item, at, days)]
    entry = {
        "hash": content_hash(path),
        "path": _relative(root, path),
        "scope": scope,
        "piece": piece,
        "at": at.isoformat(),
    }
    entries = [
        old for old in entries
        if not (old.get("hash") == entry["hash"] and old.get("scope", "") == scope)
    ]
    entries.append(entry)
    _write(target, entries)
    return entry


def find_duplicate(root, path, *, registry_path=None, now=None, days=30, scope="") -> dict | None:
    """Procura arte igual (sha256) ou recomprimida (dHash) no mesmo ``scope``."""
    at = _now(now)
    target = Path(registry_path) if registry_path is not None else Path(root) / _REGISTRY
    entries = _load(target)
    digest = content_hash(path)
    try:
        perceptual = perceptual_hash(path)
    except Exception: perceptual = None
    for entry in entries:
        if entry.get("scope", "") != scope or not _is_recent(entry, at, days):
            continue
        if entry.get("hash") == digest:
            return entry
        raw = entry.get("path")
        if perceptual is None or not isinstance(raw, str) or not raw:
            continue
        stored = Path(raw) if Path(raw).is_absolute() else Path(root) / raw
        if not stored.is_file():
            continue
        try:
            if perceptual_hash(stored) == perceptual:
                return entry
        except Exception: continue
    return None
