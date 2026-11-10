from __future__ import annotations
import json
import math

import numpy as np


def duck_envelope(total_s: float, sr: int, intervals: list[tuple[float, float, float]], ramp_s: float) -> np.ndarray:
    n = int(round(float(total_s) * int(sr)))
    if n <= 0:
        return np.ones(0, dtype=float)
    times = np.arange(n, dtype=float) / float(sr)
    env = np.ones(n, dtype=float)
    ramp = float(ramp_s)
    for ini, fim, gain in intervals:
        ini_f = float(ini)
        fim_f = float(fim)
        g = float(gain)
        if not fim_f > ini_f:
            continue
        dur = fim_f - ini_f
        if ramp > 0.0:
            r = ramp if ramp < dur / 2.0 else dur / 2.0
        else:
            r = 0.0
        cur = np.ones(n, dtype=float)
        if r > 0.0:
            m_in = (times >= ini_f) & (times < ini_f + r)
            if bool(np.any(m_in)):
                a_in = (times[m_in] - ini_f) / r
                w_in = 0.5 * (1.0 + np.cos(np.pi * a_in))
                cur[m_in] = g + (1.0 - g) * w_in
            m_mid = (times >= ini_f + r) & (times <= fim_f - r)
            if bool(np.any(m_mid)):
                cur[m_mid] = g
            m_out = (times > fim_f - r) & (times <= fim_f)
            if bool(np.any(m_out)):
                a_out = (times[m_out] - (fim_f - r)) / r
                w_out = 0.5 * (1.0 - np.cos(np.pi * a_out))
                cur[m_out] = g + (1.0 - g) * w_out
        else:
            m_mid = (times >= ini_f) & (times < fim_f)
            if bool(np.any(m_mid)):
                cur[m_mid] = g
        env = np.minimum(env, cur)
    return env


def db_to_gain(db: float) -> float:
    return 10.0 ** (float(db) / 20.0)


def _num(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} deve ser numerico")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} deve ser numerico") from None
    if not math.isfinite(number):
        raise ValueError(f"{name} deve ser finito")
    return number


def _fmt(value, name) -> str:
    return str(float(_num(value, name)))


def loudnorm_measure_cmd(wav, target, tp, lra) -> list[str]:
    filt = (
        f"loudnorm=I={_fmt(target, 'target')}:TP={_fmt(tp, 'tp')}"
        f":LRA={_fmt(lra, 'lra')}:print_format=json"
    )
    return ["ffmpeg", "-hide_banner", "-i", str(wav), "-af", filt, "-f", "null", "-"]


def _pick(measured: dict, *keys: str):
    for k in keys:
        if k in measured:
            return measured[k]
    raise KeyError(str(keys[0]))


def loudnorm_apply_cmd(wav, out, target, tp, lra, measured: dict) -> list[str]:
    mi = _pick(measured, "measured_I", "input_i", "I")
    mtp = _pick(measured, "measured_TP", "input_tp", "TP")
    mlra = _pick(measured, "measured_LRA", "input_lra", "LRA")
    mth = _pick(measured, "measured_thresh", "input_thresh", "thresh")
    moff = _pick(measured, "measured_offset", "target_offset", "offset")
    filt = (
        f"loudnorm=I={_fmt(target, 'target')}:TP={_fmt(tp, 'tp')}:LRA={_fmt(lra, 'lra')}"
        f":measured_I={_fmt(mi, 'measured_I')}:measured_TP={_fmt(mtp, 'measured_TP')}"
        f":measured_LRA={_fmt(mlra, 'measured_LRA')}"
        f":measured_thresh={_fmt(mth, 'measured_thresh')}:offset={_fmt(moff, 'measured_offset')}"
        f":linear=true"
    )
    return ["ffmpeg", "-y", "-hide_banner", "-i", str(wav), "-af", filt, str(out)]


def parse_loudnorm_json(stderr: str) -> dict:
    start = stderr.rfind("{")
    end = stderr.rfind("}")
    if start < 0 or end < 0 or end < start:
        raise ValueError("bloco JSON nao encontrado no stderr")
    return json.loads(stderr[start : end + 1])


def voice_gain_cmd(wav, out, lufs) -> list[str]:
    filt = f"loudnorm=I={_fmt(lufs, 'lufs')}:TP=-1.5:LRA=7"
    return ["ffmpeg", "-y", "-hide_banner", "-i", str(wav), "-af", filt, str(out)]
