from __future__ import annotations

# Verificacoes deterministicas de qualidade (ver DESIGN.md, secao qa.py).
import re

# Margem usada para decidir se um evento "encosta" numa tarja de nome.
# E a mesma margem de 0,2 s empregada por subs.build_subs ao marcar `raised`.
_TAG_MARGIN_S = 0.2
_MIN_DURATION_S = 0.8
_MAX_LAG_S = 0.6


def _issue(level: str, cid, code: str, msg: str) -> dict:
    return {"level": level, "id": cid, "code": code, "msg": msg}


def _words(text: str) -> list:
    """Palavras minusculas, sem pontuacao."""
    return re.findall(r"\w+", (text or "").lower())


def _edit_distance(ref: list, hyp: list) -> int:
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1]


def wer(ref: str, hyp: str) -> float:
    """Word error rate: distancia de edicao / numero de palavras da referencia."""
    ref_words = _words(ref)
    hyp_words = _words(hyp)
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    return _edit_distance(ref_words, hyp_words) / len(ref_words)


def _render_cfg(cfg: dict) -> tuple:
    render = (cfg or {}).get("render") or {}
    return (
        int(render.get("max_chars_line", 42)),
        int(render.get("max_lines", 2)),
        float(render.get("cps_max", 20.0)),
        float(render.get("fps", 30.0)),
    )


def _qa_cfg(cfg: dict) -> dict:
    return (cfg or {}).get("qa") or {}


def check_subs(subs, cfg) -> list:
    max_chars, max_lines, cps_max, _fps = _render_cfg(cfg)
    issues = []
    prev_end = None
    for sub in subs or []:
        start = float(sub.get("start", 0.0))
        end = float(sub.get("end", 0.0))
        lines = [str(line) for line in (sub.get("lines") or [])]
        cid = sub.get("id")
        duration = end - start

        if duration < _MIN_DURATION_S - 1e-9:
            issues.append(_issue(
                "error", cid, "DURATION",
                "evento dura %.2fs (minimo %.1fs)" % (duration, _MIN_DURATION_S),
            ))

        if len(lines) > max_lines:
            issues.append(_issue(
                "error", cid, "LINES",
                "evento tem %d linhas (maximo %d)" % (len(lines), max_lines),
            ))

        for line in lines:
            if len(line) > max_chars:
                issues.append(_issue(
                    "error", cid, "LINE_LONG",
                    "linha com %d caracteres (maximo %d)" % (len(line), max_chars),
                ))
                break

        text = " ".join(lines)
        if duration > 0:
            cps = len(text) / duration
            if cps > cps_max:
                issues.append(_issue(
                    "warn", cid, "CPS",
                    "%.1f caracteres/s (maximo %.1f)" % (cps, cps_max),
                ))

        if prev_end is not None and start < prev_end - 1e-9:
            issues.append(_issue(
                "warn", cid, "OVERLAP",
                "evento comeca em %.2fs, antes do fim anterior %.2fs"
                % (start, prev_end),
            ))
        prev_end = end if prev_end is None else max(prev_end, end)
    return issues


def _tag_amount(sub: dict, t0: float, t1: float) -> tuple:
    """Distancia/intersecao entre evento e janela de tarja.

    Devolve (quantidade, intersecta). Sem interseccao, a quantidade e a folga
    entre os intervalos; com interseccao, e o tamanho da sobreposicao.
    """
    start = float(sub.get("start", 0.0))
    end = float(sub.get("end", 0.0))
    if start < t1 and t0 < end:
        return min(end, t1) - max(start, t0), True
    if end <= t0:
        return t0 - end, False
    return start - t1, False


def check_overlap(subs, lower_thirds, cfg) -> list:
    _max_chars, _max_lines, _cps_max, fps = _render_cfg(cfg)
    max_frames = int(_qa_cfg(cfg).get("max_overlap_frames", 2))
    budget = max_frames / fps if fps > 0 else 0.0
    issues = []
    for sub in subs or []:
        if sub.get("raised"):
            continue
        for window in lower_thirds or []:
            t0, t1 = float(window[0]), float(window[1])
            amount, intersects = _tag_amount(sub, t0, t1)
            if intersects:
                if amount > budget + 1e-9:
                    issues.append(_issue(
                        "error", sub.get("id"), "TAG_OVERLAP",
                        "evento nao elevado sobrepoe tarja por %.2fs "
                        "(maximo %.2fs)" % (amount, budget),
                    ))
            elif budget + 1e-9 < amount <= _TAG_MARGIN_S + 1e-9:
                issues.append(_issue(
                    "error", sub.get("id"), "TAG_OVERLAP",
                    "evento nao elevado a %.2fs da tarja (tolerancia %.2fs)"
                    % (amount, budget),
                ))
    return issues


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def check_loudness(report: dict, cfg) -> list:
    qa = _qa_cfg(cfg)
    target = float(((cfg or {}).get("mix") or {}).get("target_lufs", -16.0))
    tol = float(qa.get("lufs_tol", 1.0))
    max_tp = float(qa.get("max_true_peak", -1.0))

    report = report or {}
    loudness = _as_float(report.get("I", report.get("input_i")))
    true_peak = _as_float(report.get("TP", report.get("input_tp")))

    issues = []
    if loudness is not None and abs(loudness - target) > tol + 1e-9:
        issues.append(_issue(
            "error", None, "LUFS",
            "loudness %.1f LUFS fora da meta %.1f +/- %.1f"
            % (loudness, target, tol),
        ))
    if true_peak is not None and true_peak > max_tp + 1e-9:
        issues.append(_issue(
            "error", None, "TRUE_PEAK",
            "true peak %.1f dB acima do maximo %.1f" % (true_peak, max_tp),
        ))
    return issues


_SCHEDULE_WARNINGS = {
    "TEMPO_CLAMPED": "tempo da fala foi limitado",
    "OVERFLOW": "fala ultrapassa a janela alvo",
}


def check_schedule(schedule) -> list:
    schedule = schedule or {}
    issues = []
    emitted = set()

    def _add(level: str, cid, code: str, msg: str) -> None:
        key = (level, cid, code)
        if key in emitted:
            return
        emitted.add(key)
        issues.append(_issue(level, cid, code, msg))

    for cue in schedule.get("cues") or []:
        cid = cue.get("id")
        for warning in cue.get("warnings") or []:
            if warning in _SCHEDULE_WARNINGS:
                _add("warn", cid, warning, _SCHEDULE_WARNINGS[warning])
        lag = _as_float(cue.get("lag"))
        if lag is not None and lag > _MAX_LAG_S + 1e-9:
            _add("error", cid, "LAG",
                 "lag de %.2fs (maximo %.1fs)" % (lag, _MAX_LAG_S))

    for warning in schedule.get("warnings") or []:
        if warning in _SCHEDULE_WARNINGS:
            _add("warn", None, warning, _SCHEDULE_WARNINGS[warning])

    return issues


def summarize(issues) -> dict:
    issues = list(issues or [])
    errors = sum(1 for issue in issues if issue.get("level") == "error")
    warnings = sum(1 for issue in issues if issue.get("level") == "warn")
    return {
        "ok": errors == 0,
        "errors": errors,
        "warnings": warnings,
        "issues": issues,
    }
