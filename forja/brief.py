"""Brief humano e aprovacoes: requisitos iniciais e gates de decisao."""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import yaml

from .errors import ForjaError

BRIEF_FILE = "brief.yaml"
APPROVALS_FILE = "approvals.json"
APPROVAL_KEYS = ("script", "voice", "overlays", "publish")
_REQUIRED_TEXT = ("objective", "audience", "tone")


def brief_path(root) -> Path:
    return Path(root) / BRIEF_FILE


def approvals_path(root) -> Path:
    return Path(root) / APPROVALS_FILE


def load_brief(root) -> dict | None:
    path = brief_path(root)
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ForjaError(
            "CONFIG_INVALID",
            "brief.yaml ilegivel: %s" % exc,
            hint="corrija o YAML do brief (ou rode `forja init` de novo)",
        ) from exc
    if not isinstance(data, dict):
        raise ForjaError("CONFIG_INVALID", "brief.yaml deve ser um mapeamento")
    return data


def brief_issues(root) -> list[dict]:
    """Problemas do brief como issues leves (nao bloqueiam o pipeline)."""
    issues = []
    try:
        data = load_brief(root)
    except ForjaError as exc:
        return [{"level": "error", "code": exc.code, "msg": str(exc)}]
    if data is None:
        return [
            {
                "level": "warn",
                "code": "BRIEF_MISSING",
                "msg": "brief.yaml ausente: registre objetivo, publico e tom antes de criar",
            }
        ]
    if data.get("version") != 1:
        issues.append({"level": "error", "code": "BRIEF_VERSION", "msg": "brief.version deve ser 1"})
    for key in _REQUIRED_TEXT:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(
                {
                    "level": "warn",
                    "code": "BRIEF_INCOMPLETE",
                    "msg": "brief.%s esta vazio" % key,
                }
            )
    duration = data.get("duration_s")
    if duration is not None and (
        isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0
    ):
        issues.append(
            {"level": "error", "code": "BRIEF_DURATION", "msg": "brief.duration_s deve ser positivo ou null"}
        )
    if not isinstance(data.get("consent", False), bool):
        issues.append(
            {"level": "error", "code": "BRIEF_CONSENT", "msg": "brief.consent deve ser booleano"}
        )
    for key in ("must_include", "must_avoid"):
        value = data.get(key, [])
        if not isinstance(value, list):
            issues.append(
                {"level": "error", "code": "BRIEF_LIST", "msg": "brief.%s deve ser lista" % key}
            )
    return issues


def _default_approvals() -> dict:
    data = {key: False for key in APPROVAL_KEYS}
    data.update({"by": "", "at": ""})
    return data


def load_approvals(root) -> dict:
    path = approvals_path(root)
    if not path.is_file():
        return _default_approvals()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ForjaError(
            "GATE_FAILED",
            "approvals.json ilegivel: %s" % exc,
            hint="corrija o JSON; aprovacoes nao podem falhar abertas",
        ) from exc
    if not isinstance(data, dict):
        raise ForjaError("GATE_FAILED", "approvals.json deve ser um objeto")
    result = _default_approvals()
    for key in APPROVAL_KEYS:
        if key in data:
            if not isinstance(data[key], bool):
                raise ForjaError("GATE_FAILED", "approvals.%s deve ser booleano" % key)
            result[key] = data[key]
    for key in ("by", "at"):
        if key in data:
            if not isinstance(data[key], str):
                raise ForjaError("GATE_FAILED", "approvals.%s deve ser string" % key)
            result[key] = data[key]
    return result


def write_approvals(root, updates: dict, by: str = "humano", now=None) -> dict:
    if not isinstance(updates, dict) or not updates:
        raise ForjaError("USAGE", "informe ao menos uma aprovacao")
    unknown = sorted(set(updates) - set(APPROVAL_KEYS))
    if unknown:
        raise ForjaError("USAGE", "aprovacao desconhecida: %s" % ", ".join(unknown))
    for key, value in updates.items():
        if not isinstance(value, bool):
            raise ForjaError("USAGE", "aprovacao %s deve ser booleana" % key)
    if not isinstance(by, str) or not by.strip():
        raise ForjaError("USAGE", "informe quem aprovou em --by")
    data = load_approvals(root)
    data.update(updates)
    data["by"] = by.strip()
    moment = now or datetime.datetime.now(datetime.timezone.utc)
    data["at"] = moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    path = approvals_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return data


def approval_issues(root, required=("script", "voice")) -> list[dict]:
    try:
        data = load_approvals(root)
    except ForjaError as exc:
        return [{"level": "error", "code": exc.code, "msg": str(exc)}]
    issues = []
    for key in required:
        if not data.get(key):
            issues.append(
                {
                    "level": "warn",
                    "code": "APPROVAL_PENDING",
                    "msg": "aprovacao humana pendente: %s" % key,
                }
            )
    return issues


def require_approvals(root, cfg: dict, required=("script", "voice")) -> None:
    project = cfg.get("project") if isinstance(cfg, dict) else {}
    if not isinstance(project, dict) or not project.get("require_approvals"):
        return
    data = load_approvals(root)
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise ForjaError(
            "GATE_FAILED",
            "aprovacao humana pendente: %s" % ", ".join(missing),
            hint="revise o brief/roteiro/voz e rode `forja approve --script --voice --by <nome>`",
            details={"missing": missing, "approvals": data},
        )
