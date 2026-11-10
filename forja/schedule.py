"""Planejamento deterministico da narracao (ver DESIGN.md, secao schedule.py)."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

ABS_MIN_TEMPO = 0.5
ABS_MAX_TEMPO = 2.0
OVERFLOW_LAG_S = 0.25
DEFAULT_MIN_TEMPO = 0.9
DEFAULT_MAX_TEMPO = 1.2


def _envelope(samples: np.ndarray, sr: int) -> np.ndarray:
    """Envelope absoluto suavizado por media movel de 20 ms."""
    window = max(1, int(round(float(sr) * 0.02)))
    return np.convolve(np.abs(samples), np.ones(window) / window, mode="same")


def speech_bounds(
    samples: np.ndarray, sr: int, thr: float = 0.02
) -> Optional[Tuple[float, float]]:
    """Inicio/fim (s) da fala; None quando nada passa do limiar."""
    if samples is None:
        return None
    data = np.asarray(samples)
    if data.size == 0:
        return None
    rate = float(sr) if sr else 0.0
    if rate <= 0:
        return None
    env = _envelope(data.astype(np.float64, copy=False), rate)
    above = np.flatnonzero(env > float(thr))
    if above.size == 0:
        return None
    start = float(above[0]) / rate
    end = float(above[-1] + 1) / rate
    if end <= start:
        return None
    return (start, end)


def _tempo_limits(cfg: dict) -> Tuple[float, float]:
    voices = (cfg or {}).get("voices") or {}
    try:
        min_tempo = float(voices.get("min_tempo", DEFAULT_MIN_TEMPO))
    except (TypeError, ValueError):
        min_tempo = DEFAULT_MIN_TEMPO
    try:
        max_tempo = float(voices.get("max_tempo", DEFAULT_MAX_TEMPO))
    except (TypeError, ValueError):
        max_tempo = DEFAULT_MAX_TEMPO
    lo = max(ABS_MIN_TEMPO, min_tempo)
    hi = min(ABS_MAX_TEMPO, max_tempo)
    if lo > hi:
        lo = hi
    return lo, hi


def _cue_start(cue: dict) -> float:
    return float(cue.get("t0", 0.0)) + float(cue.get("lead", 0.3))


def _speech_len(
    cid: object,
    bounds: Dict[object, Optional[Tuple[float, float]]],
    durations: Dict[object, float],
) -> float:
    bound = (bounds or {}).get(cid)
    if bound is None:
        try:
            return max(0.0, float((durations or {}).get(cid, 0.0)))
        except (TypeError, ValueError):
            return 0.0
    try:
        length = float(bound[1]) - float(bound[0])
    except (TypeError, ValueError, IndexError):
        return 0.0
    return max(0.0, length)


def plan(
    cues: Sequence[dict],
    durations: Dict[object, float],
    cfg: dict,
    total: float,
    bounds: Dict[object, Optional[Tuple[float, float]]],
) -> dict:
    """Monta o cronograma sem empurrar cues nem violar os limites de tempo."""
    lo, hi = _tempo_limits(cfg)
    ordered = sorted(cues or [], key=lambda cue: float(cue.get("t0", 0.0)))
    total_s = float(total)
    planned: List[dict] = []
    warnings: List[str] = []

    for index, cue in enumerate(ordered):
        cid = cue.get("id")
        start = _cue_start(cue)
        role = cue.get("role", "speech")
        if role == "narrator":
            if index + 1 < len(ordered):
                target = _cue_start(ordered[index + 1])
            else:
                target = total_s
        else:
            target = float(cue.get("t1", start))

        speech_len = _speech_len(cid, bounds, durations)
        window = target - start
        raw_tempo = speech_len / window if window > 0 else hi
        tempo = min(max(raw_tempo, lo), hi)
        end = start + speech_len / tempo if tempo > 0 else start
        lag = max(0.0, end - target)

        cue_warnings: List[str] = []
        if tempo != raw_tempo:
            cue_warnings.append("TEMPO_CLAMPED")
        if lag > OVERFLOW_LAG_S:
            cue_warnings.append("OVERFLOW")
        for code in cue_warnings:
            if code not in warnings:
                warnings.append(code)

        planned.append(
            {
                "id": cid,
                "start": start,
                "end": end,
                "tempo": tempo,
                "trim_start": 0.0,
                "trim_end": 0.0,
                "lag": lag,
                "warnings": cue_warnings,
            }
        )

    return {"total": total_s, "cues": planned, "warnings": warnings}
