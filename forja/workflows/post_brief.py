"""Passo `brief` do workflow post: valida o brief humano e grava work/brief.json."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .. import brief
from ..errors import ForjaError

_REQUIRED_TEXT = ("objective", "audience", "tone")


def _canonical(data) -> str:
    return json.dumps(
        data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    )


def _write_json(path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load(ctx) -> dict:
    data = brief.load_brief(ctx.root)
    if data is None:
        raise ForjaError(
            "MISSING_INPUT",
            "brief.yaml ausente: preencha o brief antes do passo brief",
            hint="rode `forja init` ou escreva brief.yaml com objective, audience e tone",
            details={"path": "brief.yaml"},
        )
    issues = brief.brief_issues(ctx.root)
    incomplete = [i for i in issues if i.get("code") == "BRIEF_INCOMPLETE"]
    if incomplete:
        missing = [
            key for key in _REQUIRED_TEXT
            if not isinstance(data.get(key), str) or not data[key].strip()
        ]
        raise ForjaError(
            "BRIEF_INCOMPLETE",
            "brief incompleto: %s" % ", ".join(missing),
            details={"missing": missing, "issues": incomplete},
        )
    blocking = [i for i in issues if i.get("level") == "error"]
    if blocking:
        raise ForjaError(
            "CONFIG_INVALID",
            blocking[0]["msg"],
            details={"issues": blocking},
        )
    return data


def run_brief(ctx) -> dict:
    """Valida o brief humano e grava a forma normalizada com o hash do brief."""
    data = _load(ctx)
    digest = hashlib.sha256(_canonical(data).encode("utf-8")).hexdigest()
    payload = dict(data)
    payload["hash"] = digest
    path = Path(ctx.work) / "brief.json"
    _write_json(path, payload)
    return {"ok": True, "hash": digest}
