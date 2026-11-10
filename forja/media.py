from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from forja import env as envmod
from forja import mixlib, render
from forja.errors import ForjaError


def _checked(cmd, run, what, **kwargs):
    """Executa `cmd` via `run` e converte falhas em ForjaError."""
    kwargs.setdefault("env", envmod.sanitized())
    try:
        result = run(cmd, capture_output=True, text=True, **kwargs)
    except FileNotFoundError as exc:
        tool = str(cmd[0]) if cmd else what
        raise ForjaError(
            "MISSING_PREREQ",
            f"{what} nao encontrado: {tool}",
            hint=f"instale {tool} e ponha no PATH",
            details={"cmd": tool, "error": str(exc)},
        ) from exc
    if result.returncode != 0:
        stderr = result.stderr or ""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        raise ForjaError(
            "PROVIDER_ERROR",
            f"{what} falhou (exit {result.returncode})",
            details={
                "cmd": str(cmd[0]) if cmd else what,
                "returncode": result.returncode,
                "stderr_tail": stderr[-500:],
            },
        )
    return result


def run_checked(cmd, run=subprocess.run, what="ffmpeg") -> subprocess.CompletedProcess:
    return _checked(cmd, run, what)


# --------------------------------------------------------------------- clip

def cut_clip_cmd(src, out, start, duration=None) -> list[str]:
    cmd = ["ffmpeg", "-y", "-ss", str(start)]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += [
        "-i",
        str(src),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        str(out),
    ]
    return cmd


def cut_clip(src, out, start, duration=None, run=subprocess.run) -> Path:
    _checked(cut_clip_cmd(src, out, start, duration), run, "ffmpeg")
    return Path(out)


# -------------------------------------------------------------------- audio

def extract_audio_cmd(src, out, sr=48000) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-vn",
        "-ac",
        "2",
        "-ar",
        str(sr),
        "-c:a",
        "pcm_s16le",
        str(out),
    ]


def extract_audio(src, out, sr=48000, run=subprocess.run) -> Path:
    _checked(extract_audio_cmd(src, out, sr), run, "ffmpeg")
    return Path(out)


def trim_tempo_cmd(wav, out, tempo, trim_silence=True) -> list[str]:
    tempo = float(tempo)
    if tempo < 0.5 or tempo > 2.0:
        raise ValueError("tempo deve estar em [0.5, 2.0]")

    filters: list[str] = []
    if trim_silence:
        filters.append(
            "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB"
        )
        filters.append("areverse")
        filters.append(
            "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB"
        )
        filters.append("areverse")
    if abs(tempo - 1.0) >= 1e-6:
        filters.append(f"atempo={tempo}")
    if not filters:
        filters.append("anull")

    return ["ffmpeg", "-y", "-i", str(wav), "-af", ",".join(filters), str(out)]


def _as_float(samples) -> np.ndarray:
    arr = np.asarray(samples)
    if arr.dtype.kind == "f":
        return arr.astype(np.float64)
    return arr.astype(np.float64) / 32768.0


def _mono(samples) -> np.ndarray:
    arr = _as_float(samples)
    if arr.ndim == 1:
        return arr
    if arr.shape[1] == 1:
        return arr[:, 0]
    return arr.mean(axis=1)


def _read_same_rate(path, sr: int) -> np.ndarray:
    actual_sr, samples = wavfile.read(str(path))
    if int(actual_sr) != int(sr):
        name = Path(path).name
        raise ForjaError(
            "CONFIG_INVALID",
            f"taxa de amostragem de {name} e {actual_sr}, esperado {sr}",
            details={"path": str(path), "expected_sr": int(sr), "actual_sr": int(actual_sr)},
        )
    return samples


def assemble_mix(orig_wav, voices, duck_intervals, cfg, out, sr=48000) -> Path:
    sr = int(sr)
    orig = _as_float(_read_same_rate(orig_wav, sr))
    if orig.ndim == 1:
        stereo = np.column_stack([orig, orig])
    elif orig.shape[1] == 1:
        stereo = np.repeat(orig, 2, axis=1)
    else:
        stereo = orig[:, :2]

    total_s = stereo.shape[0] / float(sr)
    mix_cfg = cfg.get("mix", {}) if isinstance(cfg, dict) else {}
    orig_gain = float(mix_cfg.get("orig_gain", 1.0))
    ramp_s = float(mix_cfg.get("ramp_s", 0.3))
    # `duck_intervals` chega em dB; duck_envelope trabalha com ganho linear.
    gains = [
        (float(ini), float(fim), mixlib.db_to_gain(float(db)))
        for ini, fim, db in duck_intervals
    ]
    env = mixlib.duck_envelope(total_s, sr, gains, ramp_s)
    mixed = stereo * orig_gain * env[:, None]

    for item in voices:
        wav = item["wav"]
        start = float(item["start"])
        voice = _mono(_read_same_rate(wav, sr))
        start_sample = int(round(start * sr))
        offset = 0
        if start_sample < 0:
            offset = -start_sample
            start_sample = 0
        if offset >= voice.shape[0] or start_sample >= mixed.shape[0]:
            continue
        chunk = voice[offset:]
        room = mixed.shape[0] - start_sample
        chunk = chunk[:room]
        mixed[start_sample : start_sample + chunk.shape[0], 0] += chunk
        mixed[start_sample : start_sample + chunk.shape[0], 1] += chunk

    peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
    if peak > 0.98:
        mixed *= 0.98 / peak

    data = np.clip(np.rint(mixed * 32767.0), -32768, 32767).astype(np.int16)
    wavfile.write(str(out), sr, data)
    return Path(out)


# ----------------------------------------------------------------- loudness

def measure_loudness(wav, cfg, run=subprocess.run) -> dict:
    mix_cfg = cfg["mix"]
    cmd = mixlib.loudnorm_measure_cmd(
        wav, mix_cfg["target_lufs"], mix_cfg["true_peak"], mix_cfg["lra"]
    )
    result = _checked(cmd, run, "ffmpeg")
    stderr = result.stderr or ""
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", errors="replace")
    return mixlib.parse_loudnorm_json(stderr)


def normalize_loudness(wav, out, cfg, run=subprocess.run) -> dict:
    measured = measure_loudness(wav, cfg, run=run)
    mix_cfg = cfg["mix"]
    cmd = mixlib.loudnorm_apply_cmd(
        wav,
        out,
        mix_cfg["target_lufs"],
        mix_cfg["true_peak"],
        mix_cfg["lra"],
        measured,
    )
    _checked(cmd, run, "ffmpeg")
    return measured


# ------------------------------------------------------------------- render

def render_remotion(entry, props, public_dir, out, run=subprocess.run, cwd=None, composition="Legendas") -> Path:
    out = Path(out)
    props_path = Path(str(out) + ".props.json")
    props_path.parent.mkdir(parents=True, exist_ok=True)
    props_path.write_text(
        json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    cmd = render.remotion_cmd(entry, str(props_path), str(public_dir), str(out), composition)
    kwargs = {"cwd": str(cwd)} if cwd is not None else {}
    if cwd is not None:
        local = Path(cwd) / "node_modules" / ".bin"
        for name in ("remotion", "remotion.cmd", "remotion.exe"):
            candidate = local / name
            if candidate.is_file():
                cmd[0] = str(candidate)
                break
    _checked(cmd, run, "remotion", **kwargs)
    return out


def mux(video, wav, out, run=subprocess.run) -> Path:
    _checked(render.mux_cmd(video, wav, str(out)), run, "ffmpeg")
    return Path(out)


def contact_sheet(video, out, duration_s, n=12, cols=4, run=subprocess.run) -> Path:
    duration = float(duration_s)
    if duration <= 0:
        raise ValueError("duration_s deve ser > 0")
    n = int(n)
    cols = int(cols)
    if n <= 0 or cols <= 0:
        raise ValueError("n e cols devem ser > 0")
    rows = int(math.ceil(n / cols))
    vf = f"fps={n}/{duration},scale=320:-1,tile={cols}x{rows}"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-vf",
        vf,
        "-frames:v",
        "1",
        str(out),
    ]
    _checked(cmd, run, "ffmpeg")
    return Path(out)
