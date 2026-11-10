from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

_MISSING = "MISSING"
_CHUNK = 1024 * 1024


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(_CHUNK)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _path_label(path: Path) -> str:
    """Rótulo relativo ao diretório atual (estável e independente do host)."""
    try:
        resolved = path.resolve()
        cwd = Path.cwd().resolve()
    except (ValueError, OSError):
        return path.name
    try:
        return resolved.relative_to(cwd).as_posix()
    except ValueError:
        pass
    try:
        return Path(os.path.relpath(resolved, cwd)).as_posix()
    except (ValueError, OSError):
        return path.name


def _canonical(value) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def hash_inputs(paths, extra=None) -> str:
    """sha256 de caminho + tamanho + conteúdo de cada entrada, mais ``extra``."""
    records = []
    for raw in paths:
        path = Path(raw)
        label = _path_label(path)
        if path.is_file():
            records.append(
                {"path": label, "size": path.stat().st_size, "sha256": _file_sha256(path)}
            )
        else:
            records.append({"path": label, "missing": _MISSING})
    records.sort(key=_canonical)
    digest = hashlib.sha256()
    for record in records:
        digest.update(_canonical(record).encode("utf-8"))
        digest.update(b"\n")
    digest.update(_canonical(extra).encode("utf-8"))
    return digest.hexdigest()


class Manifest:
    """Mapa passo -> {input_hash, outputs}, persistido em JSON legível."""

    def __init__(self, path):
        self.path = Path(path)
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return
        if isinstance(data, dict):
            self._data = data

    def get(self, step) -> dict | None:
        entry = self._data.get(step)
        return entry if isinstance(entry, dict) else None

    def put(self, step, input_hash, outputs: list) -> None:
        self._data[step] = {
            "input_hash": input_hash,
            "outputs": [str(output) for output in outputs],
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def is_fresh(self, step, input_hash, outputs) -> bool:
        entry = self.get(step)
        if entry is None or entry.get("input_hash") != input_hash:
            return False
        return all(Path(output).exists() for output in outputs)
