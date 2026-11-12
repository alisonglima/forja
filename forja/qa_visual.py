"""QA visual de pecas: dimensoes, contraste sobre foto e dedup por sha256.

Orquestra `qa_geometry.measure` e emite issues no formato de `forja.qa`
(`level`, `id`, `code`, `msg`). Dimensao/escala ficam em `qa_geometry.py`;
capturas 360/1280 ficam em `qa_capture.py`.
"""
from __future__ import annotations

import datetime
from pathlib import Path

from forja import qa_geometry

DEDUP_DAYS = 30
_CONTRAST = 4.5
_CONTRAST_LARGE = 3.0


def _issue(level: str, cid, code: str, msg: str) -> dict:
    return {"level": level, "id": cid, "code": code, "msg": msg}


def _summary(issues) -> dict:
    issues = list(issues or [])
    errors = sum(1 for issue in issues if issue.get("level") == "error")
    return {"ok": errors == 0, "issues": issues}


def _now(value):
    """Normaliza `now` (ISO ou datetime) para datetime com timezone UTC."""
    if isinstance(value, datetime.datetime):
        at = value
    elif isinstance(value, str):
        at = datetime.datetime.fromisoformat(value)
    else:
        at = datetime.datetime.now(datetime.timezone.utc)
    return at if at.tzinfo else at.replace(tzinfo=datetime.timezone.utc)


def _recent(entry: dict, now: datetime.datetime, days: int = DEDUP_DAYS) -> bool:
    """Indica se a entrada tem `at` entre `now - days` e `now`."""
    raw = entry.get("at")
    if not isinstance(raw, str):
        return False
    try:
        at = datetime.datetime.fromisoformat(raw)
    except ValueError:
        return False
    if at.tzinfo is None:
        at = at.replace(tzinfo=datetime.timezone.utc)
    delta = now - at
    return datetime.timedelta(0) <= delta <= datetime.timedelta(days=days)


def _duplicate(entry: dict, digest: str, brand_id) -> dict | None:
    """Issue DUPLICATE_ARTIFACT se o hash repete no mesmo scope e na janela."""
    if not brand_id or entry.get("scope") != brand_id:
        return None
    if str(entry.get("hash") or "").lower() != digest.lower():
        return None
    path = entry.get("path") or "?"
    at = str(entry.get("at") or "")[:10]
    return _issue(
        "error", "sha256", "DUPLICATE_ARTIFACT",
        "ja existe arte com este sha256 em %s (registrada em %s)" % (path, at),
    )


def _contrast_issues(items) -> list:
    """Aponta razoes abaixo do piso (4.5:1; 3:1 para texto grande)."""
    issues = []
    for item in items or []:
        try:
            ratio = float(item.get("ratio"))
        except (TypeError, ValueError):
            continue
        floor = _CONTRAST_LARGE if item.get("large_text") else _CONTRAST
        if ratio + 1e-9 < floor:
            issues.append(_issue(
                "error", item.get("id"), "CONTRAST_PHOTO",
                "contraste %.2f:1 abaixo de %.1f:1 na regiao sob o texto"
                % (ratio, floor),
            ))
    return issues


def inspect_artifact(path, expected, *, brand_id="", hashes=None,
                     contrast=None, now=None) -> dict:
    """Inspeciona PNG/peca final e devolve `ok`, `issues`, dimensoes e sha256.

    `hashes` traz o registro `{hash,path,scope,piece,at}` do dedup; `contrast`
    traz as razoes ja medidas na regiao sob o texto. Entradas ausentes nao
    geram issue.
    """
    measured = qa_geometry.measure(path)
    if measured is None:
        name = Path(path).name
        return {**_summary([_issue(
            "error", name, "GATE_FAILED",
            "PNG ausente, truncado ou ilegivel: %s" % name,
        )]), "width": None, "height": None, "sha256": None}

    width, height = measured["width"], measured["height"]
    expected_w, expected_h = int(expected[0]), int(expected[1])
    if (width, height) != (expected_w, expected_h):
        return {**_summary([_issue(
            "error", "dimensoes", "FORMAT_UNSUPPORTED",
            "dimensoes %dx%d (esperado %dx%d)" % (
                width, height, expected_w, expected_h),
        )]), "width": width, "height": height,
            "sha256": measured["sha256"]}

    issues = []
    digest = measured["sha256"]
    at = _now(now)
    for entry in hashes or []:
        if not isinstance(entry, dict) or not _recent(entry, at):
            continue
        issue = _duplicate(entry, digest, brand_id)
        if issue is not None:
            issues.append(issue)
    issues.extend(_contrast_issues(contrast))

    return {**_summary(issues), "width": width, "height": height,
            "sha256": digest}


def inspect_lote(pieces, *, brand_id="", hashes=None, contrast=None,
                 now=None) -> dict:
    """Inspeciona cada peca e prefixa suas issues com `piece`."""
    issues = []
    for piece in pieces or []:
        result = inspect_artifact(
            piece.get("path"), piece.get("expected"), brand_id=brand_id,
            hashes=hashes, contrast=piece.get("contrast", contrast), now=now)
        name = piece.get("piece")
        issues.extend({"piece": name, **issue} for issue in result["issues"])
    return _summary(issues)
