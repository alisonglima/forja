from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_EVENTS_FILE = "events.ndjson"
_SENSITIVE = ("key", "token", "secret", "password")


def _is_sensitive(name) -> bool:
    lowered = str(name).lower()
    return any(part in lowered for part in _SENSITIVE)


def _plain(value):
    """Converte Paths (inclusive aninhados) em strings JSON-safe."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {
            key: _plain(item)
            for key, item in value.items()
            if not _is_sensitive(key)
        }
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def emit(work_dir, step, status, **fields) -> dict:
    """Anexa um evento NDJSON em ``<work_dir>/events.ndjson`` e o devolve."""
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    event = _plain(fields)
    event["t"] = _now_utc()
    event["step"] = step
    event["status"] = status
    line = json.dumps(event, ensure_ascii=False)
    with (work / _EVENTS_FILE).open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return event


def read_events(work_dir, limit=50) -> list[dict]:
    """Devolve os últimos ``limit`` eventos, em ordem cronológica."""
    if limit is not None and limit <= 0:
        return []
    path = Path(work_dir) / _EVENTS_FILE
    if not path.is_file():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    if limit is None:
        return events
    return events[-limit:]
