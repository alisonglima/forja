from __future__ import annotations

import copy


def build_props(clip_name, total, subs, lower_thirds, cfg) -> dict:
    render_cfg = cfg.get("render", {}) if isinstance(cfg, dict) else {}
    width = render_cfg.get("width", 1280)
    height = render_cfg.get("height", 720)
    fps = render_cfg.get("fps", 30)
    font_size = render_cfg.get("font_size", 32)
    return {
        "clip": clip_name,
        "durationS": float(total),
        "fps": fps,
        "width": width,
        "height": height,
        "fontSize": font_size,
        "subs": copy.deepcopy(subs),
        "lowerThirds": copy.deepcopy(lower_thirds),
        "brand": copy.deepcopy(cfg.get("brand") or {}) if isinstance(cfg, dict) else {},
    }


def remotion_cmd(entry, props_path, public_dir, out, composition="Legendas") -> list[str]:
    return [
        "remotion",
        "render",
        entry,
        composition,
        out,
        "--props",
        props_path,
        "--public-dir",
        public_dir,
    ]


def mux_cmd(video, wav, out) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        video,
        "-i",
        wav,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        out,
    ]
