from __future__ import annotations
import json
import pathlib

from . import ids
from .errors import ForjaError

ISSUE = {"level": "error", "id": None, "code": "", "msg": ""}

_PUNCT = (",", ";", ":", ".", "?", "!")


def _make_issue(level, id, code, msg):
    return {"level": level, "id": id, "code": code, "msg": msg}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _ends_punct(word):
    return bool(word) and word[-1] in _PUNCT


def load_cues(path) -> list[dict]:
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ForjaError(
            "CONFIG_INVALID",
            "cues.json deve ser uma lista de objetos",
            hint="cada fala e um objeto com id, t0, t1 e text",
        )
    for index, cue in enumerate(data):
        if not isinstance(cue, dict):
            raise ForjaError(
                "CONFIG_INVALID",
                "cues.json: item %d nao e um objeto" % index,
                hint="cada fala e um objeto com id, t0, t1 e text",
            )
        if "lead" not in cue:
            cue["lead"] = 0.3
        if "role" not in cue:
            cue["role"] = "speech"
    return data


def estimate_duration_s(text: str) -> float:
    if not isinstance(text, str):
        return 0.0
    words = text.split()
    if not words:
        return 0.0
    return len(words) / 2.8


def split_lines(text, max_chars, max_lines) -> list[str] | None:
    if not isinstance(text, str):
        return None
    words = text.split()
    if not words:
        return []
    if max_chars <= 0 or max_lines <= 0:
        return None
    for word in words:
        if len(word) > max_chars:
            return None
    n = len(words)
    _inf = float("inf")
    _best_lines = [_inf] * (n + 1)
    _best_score = [0] * (n + 1)
    _best_next = [None] * (n + 1)
    _best_lines[n] = 0
    _best_score[n] = 0
    _best_next[n] = n
    for i in range(n - 1, -1, -1):
        cur_len = 0
        for j in range(i + 1, n + 1):
            if j == i + 1:
                cur_len = len(words[i])
            else:
                cur_len += 1 + len(words[j - 1])
            if cur_len > max_chars:
                break
            if _best_lines[j] == _inf:
                continue
            cand_lines = 1 + _best_lines[j]
            punct = 1 if (j < n and _ends_punct(words[j - 1])) else 0
            cand_score = punct + _best_score[j]
            if cand_lines < _best_lines[i] or (
                cand_lines == _best_lines[i] and cand_score > _best_score[i]
            ) or (
                cand_lines == _best_lines[i]
                and cand_score == _best_score[i]
                and (_best_next[i] is None or j > _best_next[i])
            ):
                _best_lines[i] = cand_lines
                _best_score[i] = cand_score
                _best_next[i] = j
    if _best_lines[0] == _inf or _best_lines[0] > max_lines:
        return None
    lines = []
    i = 0
    while i < n:
        j = _best_next[i]
        if j is None:
            return None
        lines.append(" ".join(words[i:j]))
        i = j
    return lines


def validate_cues(cues, cfg) -> list[dict]:
    issues = []
    if not cues:
        return []
    render = cfg.get("render", {}) if isinstance(cfg, dict) else {}
    voices = cfg.get("voices", {}) if isinstance(cfg, dict) else {}
    max_chars = render.get("max_chars_line", 42)
    max_lines = render.get("max_lines", 2)
    cps_max = render.get("cps_max", 20.0)
    max_tempo = voices.get("max_tempo", 1.2)
    seen = set()
    prev_t1 = None
    for cue in cues:
        if not isinstance(cue, dict):
            issues.append(_make_issue("error", None, "SCHEMA", "cue nao e um objeto"))
            continue
        cid = cue.get("id")
        for field in ("id", "t0", "t1", "text"):
            if field not in cue or cue[field] is None:
                issues.append(
                    _make_issue("error", cid, "MISSING_FIELD", f"campo ausente: {field}")
                )
        if "id" in cue and cue["id"] is not None:
            if not ids.is_safe_id(cue["id"]):
                issues.append(
                    _make_issue(
                        "error",
                        cid,
                        "BAD_ID",
                        "id invalido para nome de arquivo: %r" % (cid,),
                    )
                )
            try:
                if cue["id"] in seen:
                    issues.append(
                        _make_issue("error", cid, "DUP_ID", f"id duplicado: {cid}")
                    )
                else:
                    seen.add(cue["id"])
            except TypeError:
                pass
        t0 = cue.get("t0")
        t1 = cue.get("t1")
        if (
            "t0" in cue
            and "t1" in cue
            and cue["t0"] is not None
            and cue["t1"] is not None
            and _is_number(t0)
            and _is_number(t1)
        ):
            try:
                if t1 <= t0:
                    issues.append(
                        _make_issue("error", cid, "T_ORDER", f"t1 <= t0: {t0} {t1}")
                    )
            except TypeError:
                pass
        text = cue.get("text")
        if "text" in cue and isinstance(text, str):
            try:
                if split_lines(text, max_chars, max_lines) is None:
                    issues.append(
                        _make_issue(
                            "error", cid, "LINES", f"texto nao cabe em {max_lines} linhas"
                        )
                    )
            except Exception:
                issues.append(
                    _make_issue(
                        "error", cid, "LINES", f"texto nao cabe em {max_lines} linhas"
                    )
                )
            if (
                _is_number(t0)
                and _is_number(t1)
                and _is_number(cps_max)
                and (t1 - t0) > 0
            ):
                try:
                    cps = len(text) / (t1 - t0)
                    if cps > cps_max:
                        issues.append(
                            _make_issue("warn", cid, "CPS", f"cps alto: {cps:.2f}")
                        )
                except Exception:
                    pass
            lead = cue.get("lead", 0.3)
            if lead is None:
                lead = 0.3
            if (
                _is_number(t0)
                and _is_number(t1)
                and _is_number(lead)
                and _is_number(max_tempo)
            ):
                try:
                    est = estimate_duration_s(text)
                    budget = (t1 - t0 - lead) * max_tempo * 1.1
                    if est > budget:
                        issues.append(
                            _make_issue(
                                "error",
                                cid,
                                "BUDGET",
                                f"duracao estimada {est:.2f}s excede janela {budget:.2f}s",
                            )
                        )
                except Exception:
                    pass
        if _is_number(t0) and _is_number(prev_t1):
            try:
                if t0 < prev_t1:
                    issues.append(
                        _make_issue("warn", cid, "OVERLAP", f"sobrepoe anterior: {t0}")
                    )
            except TypeError:
                pass
        if _is_number(t1):
            prev_t1 = t1
    return issues
