from __future__ import annotations

import json
import subprocess

from . import env as envmod


def _parse_rate(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if "/" in text:
            num, den = text.split("/", 1)
            n = float(num)
            d = float(den)
            if d == 0:
                return None
            return n / d
        return float(text)
    except (ValueError, TypeError):
        return None


def _parse_fps(stream: dict) -> float | None:
    for key in ("r_frame_rate", "avg_frame_rate"):
        fps = _parse_rate(stream.get(key))
        if fps is not None and fps > 0:
            return float(fps)
    return None


def probe_video(path, run=subprocess.run) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = run(cmd, capture_output=True, text=True, env=envmod.sanitized())
    stdout = result.stdout
    if isinstance(stdout, bytes):
        stdout = stdout.decode("utf-8", errors="replace")
    data = json.loads(stdout)
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise RuntimeError("nenhuma stream de video encontrada")
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    raw_duration = video.get("duration")
    if raw_duration is None:
        raw_duration = (data.get("format") or {}).get("duration")
    try:
        duration = float(raw_duration)
    except (TypeError, ValueError):
        raise RuntimeError("duracao invalida no ffprobe")
    try:
        width = int(video["width"])
        height = int(video["height"])
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("dimensoes invalidas no ffprobe")
    fps = _parse_fps(video)
    if fps is None:
        raise RuntimeError("fps invalido no ffprobe")
    return {
        "duration": float(duration),
        "width": width,
        "height": height,
        "fps": float(fps),
        "has_audio": bool(has_audio),
    }
