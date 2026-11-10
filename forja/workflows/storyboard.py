from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml
from scipy.io import wavfile

from .. import cues as cues_mod
from .. import ids
from .. import media, mixlib, probe, qa, schedule, storyboard as storyboard_mod, tts
from ..errors import ForjaError
from ..steps import Step
from . import WORKFLOWS, register_workflow
from .dub import _http_post, _read_json, _wav_duration, _write_json


# --------------------------------------------------------------------- apoio


def _root_path(ctx, value) -> Path:
    """Caminho relativo a raiz do projeto; absoluto ou com ".." e recusado."""
    from forja.errors import ForjaError

    path = Path(value)
    if path.is_absolute():
        raise ForjaError(
            "CONFIG_INVALID",
            "caminho absoluto nao permitido no storyboard: %s" % value,
            hint="use um caminho relativo a raiz do projeto (ex.: assets/clipe.mp4)",
        )
    root = Path(ctx.root).resolve()
    target = (root / path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ForjaError(
            "CONFIG_INVALID",
            "caminho fora do projeto: %s" % value,
            hint="assets devem ficar dentro da pasta do projeto",
        ) from None
    return target


def _storyboard_path(ctx) -> Path:
    return ctx.root / "storyboard.yaml"


def _load_storyboard(ctx):
    path = _storyboard_path(ctx)
    if not path.is_file():
        raise ForjaError(
            "MISSING_INPUT",
            "storyboard.yaml nao encontrado",
            details={"path": "storyboard.yaml"},
        )
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _storyboard_optional(ctx):
    path = _storyboard_path(ctx)
    if not path.is_file():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None


def _scenes(sb) -> list:
    if not isinstance(sb, dict):
        return []
    scenes = sb.get("scenes")
    if not isinstance(scenes, list):
        return []
    return [scene for scene in scenes if isinstance(scene, dict)]


def _layers(scene) -> list:
    layers = scene.get("layers") if isinstance(scene, dict) else None
    return [layer for layer in layers if isinstance(layer, dict)] if isinstance(layers, list) else []


def _has_layer(scene, layer_type) -> bool:
    return any(layer.get("type") == layer_type for layer in _layers(scene))


def _narrated_scenes(sb) -> list:
    result = []
    for scene in _scenes(sb):
        scene_id = scene.get("id")
        if scene_id is None or scene_id == "":
            continue
        for layer in _layers(scene):
            if layer.get("type") == "narration":
                result.append((str(scene_id), layer, scene))
                break
    return result


def _pad_before(scene) -> float:
    duration = scene.get("duration") if isinstance(scene, dict) else None
    value = duration.get("pad_before", 0.0) if isinstance(duration, dict) else 0.0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return 0.0


def _music_layer(sb):
    for scene in _scenes(sb):
        for layer in _layers(scene):
            if layer.get("type") == "music":
                return layer
    return None


def _asset_paths(ctx, sb) -> list:
    paths = []
    seen = set()
    for scene in _scenes(sb):
        for layer in _layers(scene):
            for field in ("file", "asset", "track"):
                value = layer.get(field)
                if not isinstance(value, str) or not value:
                    continue
                path = _root_path(ctx, value)
                key = str(path)
                if key not in seen:
                    seen.add(key)
                    paths.append(path)
    return paths


def _mix_warnings(sb) -> list:
    warnings = []
    for scene in _scenes(sb):
        for layer in _layers(scene):
            layer_type = layer.get("type")
            if layer_type == "clip":
                audio = layer.get("audio")
                mode = audio.get("mode") if isinstance(audio, dict) else None
                if mode in ("keep", "duck") and "CLIP_AUDIO_IGNORED" not in warnings:
                    warnings.append("CLIP_AUDIO_IGNORED")
            elif layer_type == "sfx" and "SFX_IGNORED" not in warnings:
                warnings.append("SFX_IGNORED")
    return warnings


def _narration_duration(path) -> float:
    """Duracao do trecho com fala; cai para a do WAV quando nao ha fala."""
    try:
        rate, samples = wavfile.read(str(path))
    except (OSError, ValueError):
        return _wav_duration(path)
    data = np.asarray(samples)
    if data.ndim > 1:
        data = data.mean(axis=1)
    bounds = schedule.speech_bounds(data, int(rate))
    if bounds is None:
        return _wav_duration(path)
    return float(bounds[1] - bounds[0])


def _fallback_lines(text) -> list:
    words = str(text or "").split()
    if not words:
        return []
    half = (len(words) + 1) // 2
    if half >= len(words):
        return [" ".join(words)]
    return [" ".join(words[:half]), " ".join(words[half:])]


def _scene_start(timeline, scene_id) -> float:
    for scene in timeline.get("scenes") or []:
        if isinstance(scene, dict) and str(scene.get("id")) == str(scene_id):
            return float(scene.get("start", 0.0))
    return 0.0


def _db(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return ("%g" % number) + "dB"


def _build_bed(ctx, sb, total_s, out) -> None:
    total = "%.6f" % float(total_s)
    music = _music_layer(sb)
    if music is not None:
        track = _root_path(ctx, music.get("track", ""))
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(track),
            "-af",
            "volume=%s,apad" % _db(music.get("gain_db", 0)),
            "-t",
            total,
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(out),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=stereo",
            "-t",
            total,
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(out),
        ]
    media.run_checked(cmd)


def _remotion_entry(ctx):
    template = ctx.env.get("FORJA_REMOTION_DIR")
    if not template:
        template = Path(__file__).resolve().parents[2] / "remotion-template"
    template = Path(template)
    return template / "src" / "index.jsx", template


# ------------------------------------------------------------------- passos


def _run_validate(ctx):
    sb = _load_storyboard(ctx)
    issues = storyboard_mod.validate_storyboard(sb, ctx.root)
    summary = qa.summarize(issues)
    _write_json(ctx.work / "validate.json", summary)
    if summary["errors"]:
        raise ForjaError(
            "GATE_FAILED",
            "storyboard.yaml tem %d erro(s)" % summary["errors"],
            details={"issues": issues},
        )
    return {"ok": summary["ok"], "errors": summary["errors"], "warnings": summary["warnings"]}


def _run_voices(ctx):
    sb = _load_storyboard(ctx)
    voices_dir = ctx.work / "voices"
    voices_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = ctx.work / "cache" / "tts"
    mix_cfg = ctx.cfg.get("mix") or {}
    voice_lufs = float(mix_cfg.get("voice_lufs", -18.0))
    manifest = {}
    for scene_id, layer, _scene in _narrated_scenes(sb):
        scene_id = ids.require_safe_id(scene_id, "id da cena")
        cue = {
            "id": scene_id,
            "text": layer.get("text", ""),
            "voice": layer.get("voice"),
            "style": layer.get("style"),
        }
        source = tts.source_for(
            cue,
            ctx.cfg,
            ctx.root,
            cache_dir,
            post=_http_post,
            env=ctx.env,
        )
        target = voices_dir / (scene_id + ".wav")
        cmd = mixlib.voice_gain_cmd(source, target, voice_lufs)
        # O loudnorm do ffmpeg devolve 192 kHz; fixa a taxa para um WAV legivel.
        cmd = cmd[:-1] + ["-ar", "48000", cmd[-1]]
        media.run_checked(cmd)
        manifest[scene_id] = {
            "wav": "work/voices/%s.wav" % scene_id,
            "duration": _narration_duration(target),
        }
    _write_json(voices_dir / "manifest.json", manifest)
    return {"voices": len(manifest)}


def _run_timeline(ctx):
    sb = _load_storyboard(ctx)
    manifest = _read_json(ctx.work / "voices" / "manifest.json", {})
    narration_s = {
        str(scene_id): float(entry.get("duration", 0.0))
        for scene_id, entry in (manifest or {}).items()
        if isinstance(entry, dict)
    }
    timeline = storyboard_mod.resolve_timeline(sb, narration_s, words=None)
    _write_json(ctx.work / "timeline.json", timeline)

    render_cfg = ctx.cfg.get("render") or {}
    max_chars = int(render_cfg.get("max_chars_line", 42))
    max_lines = int(render_cfg.get("max_lines", 2))
    texts = {}
    for scene_id, narration, scene in _narrated_scenes(sb):
        if not _has_layer(scene, "captions"):
            continue
        text = str(narration.get("text") or "")
        lines = cues_mod.split_lines(text, max_chars, max_lines)
        if lines is None:
            lines = _fallback_lines(text)
        texts[scene_id] = lines

    ctx.out.mkdir(parents=True, exist_ok=True)
    (ctx.out / "legendas.srt").write_text(
        storyboard_mod.to_srt(timeline, texts), encoding="utf-8"
    )

    events = []
    for scene in timeline.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        lines = texts.get(str(scene.get("id")))
        if not lines:
            continue
        captions = None
        for layer in scene.get("layers") or []:
            if isinstance(layer, dict) and layer.get("type") == "captions":
                captions = layer
                break
        if captions is None:
            continue
        events.append(
            {
                "start": float(captions.get("start", scene.get("start", 0.0))),
                "end": float(captions.get("end", scene.get("end", 0.0))),
                "lines": lines,
                "narrador": False,
                "raised": False,
            }
        )
    _write_json(ctx.work / "subs.json", events)
    return {
        "scenes": len(timeline.get("scenes") or []),
        "subs": len(events),
    }


def _run_mix(ctx):
    timeline = _read_json(ctx.work / "timeline.json", {})
    manifest = _read_json(ctx.work / "voices" / "manifest.json", {})
    sb = _load_storyboard(ctx)
    total_s = float(timeline.get("total_s", 0.0))

    bed = ctx.work / "bed.wav"
    _build_bed(ctx, sb, total_s, bed)

    voices_dir = ctx.work / "voices"
    voices_dir.mkdir(parents=True, exist_ok=True)
    mix_cfg = ctx.cfg.get("mix") or {}
    duck_default = float(mix_cfg.get("duck_narrator_db", -20.0))
    voice_items = []
    duck_intervals = []
    for scene_id, layer, scene in _narrated_scenes(sb):
        entry = (manifest or {}).get(scene_id) or {}
        source = _root_path(ctx, entry.get("wav", ""))
        if not source.is_file():
            continue
        fit = voices_dir / (scene_id + ".fit.wav")
        cmd = media.trim_tempo_cmd(source, fit, 1.0)
        # Contrato do passo: o WAV encaixado e sempre 48 kHz mono.
        cmd = cmd[:-1] + ["-ar", "48000", "-ac", "1", cmd[-1]]
        media.run_checked(cmd)

        start = _scene_start(timeline, scene_id) + _pad_before(scene)
        end = start + _wav_duration(fit)
        voice_items.append({"wav": fit, "start": start})
        duck_db = float(layer.get("ducking_db", duck_default))
        # `media.assemble_mix` espera dB e aplica `db_to_gain` internamente.
        duck_intervals.append((start, end, duck_db))

    mix_config = {**ctx.cfg, "mix": {**mix_cfg, "orig_gain": 1.0}}
    raw = ctx.work / "mix_raw.wav"
    media.assemble_mix(bed, voice_items, duck_intervals, mix_config, raw)
    # O loudnorm cai para o modo dinamico (e devolve 192 kHz) quando o LRA
    # medido nao cabe na meta; a entrega e sempre 48 kHz estereo.
    normalized = ctx.work / "mix_normalized.wav"
    media.normalize_loudness(raw, normalized, ctx.cfg)
    media.run_checked(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(normalized),
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(ctx.work / "mix.wav"),
        ]
    )
    normalized.unlink(missing_ok=True)
    measured = media.measure_loudness(ctx.work / "mix.wav", ctx.cfg)
    loudness = {
        "I": measured.get("input_i"),
        "TP": measured.get("input_tp"),
    }
    _write_json(ctx.work / "loudness.json", loudness)
    return {
        "voices": len(voice_items),
        "I": loudness["I"],
        "warnings": _mix_warnings(sb),
    }


def _run_render(ctx):
    timeline = _read_json(ctx.work / "timeline.json", {})
    events = _read_json(ctx.work / "subs.json", [])
    sb = _load_storyboard(ctx)
    canvas = sb.get("canvas") if isinstance(sb, dict) else None
    canvas = canvas if isinstance(canvas, dict) else {}
    render_cfg = ctx.cfg.get("render") or {}
    total = float(timeline.get("total_s", 0.0))

    props = {
        "timeline": timeline,
        "subs": events,
        "lowerThirds": [],
        "fps": canvas.get("fps", render_cfg.get("fps", 30)),
        "width": canvas.get("w", render_cfg.get("width", 1280)),
        "height": canvas.get("h", render_cfg.get("height", 720)),
        "fontSize": render_cfg.get("font_size", 32),
        "durationS": total,
    }
    entry, template = _remotion_entry(ctx)
    rendered = ctx.work / "render.mp4"

    media.render_remotion(
        entry,
        props,
        public_dir=ctx.root,
        out=rendered,
        cwd=template,
        composition="Storyboard",
    )
    ctx.out.mkdir(parents=True, exist_ok=True)
    media.mux(rendered, ctx.work / "mix.wav", ctx.out / "video.mp4")
    return {"video": "out/video.mp4", "duration": total}


def _run_qa(ctx):
    events = _read_json(ctx.work / "subs.json", [])
    loudness = _read_json(ctx.work / "loudness.json", {})
    timeline = _read_json(ctx.work / "timeline.json", {})

    issues = []
    issues.extend(qa.check_subs(events, ctx.cfg))
    issues.extend(qa.check_loudness(loudness, ctx.cfg))

    total = float(timeline.get("total_s", 0.0))
    info = probe.probe_video(ctx.out / "video.mp4")
    duration = float(info.get("duration", 0.0))
    if abs(duration - total) > 0.5:
        issues.append(
            {
                "level": "error",
                "id": None,
                "code": "DURATION_MISMATCH",
                "msg": "video dura %.2fs, timeline tem %.2fs" % (duration, total),
            }
        )

    summary = qa.summarize(issues)
    _write_json(ctx.out / "qa.json", summary)
    if summary["errors"]:
        raise ForjaError(
            "GATE_FAILED",
            "QA reprovado: %d erro(s)" % summary["errors"],
            details={"issues": issues},
        )
    return {"ok": summary["ok"], "errors": summary["errors"], "warnings": summary["warnings"]}


# ------------------------------------------------------- entradas e saidas


def _inputs_validate(ctx):
    return [_storyboard_path(ctx), ctx.root / "config.yaml"], {}


def _inputs_voices(ctx):
    mix_cfg = ctx.cfg.get("mix") or {}
    paths = [_storyboard_path(ctx), ctx.root / "config.yaml"]
    if str((ctx.cfg.get("voices") or {}).get("provider", "files")) == "files":
        paths.extend(sorted((ctx.root / tts.input_dir(ctx.cfg)).glob("*.wav")))
    return (
        paths,
        {
            "voices": ctx.cfg.get("voices"),
            "mix": {"voice_lufs": mix_cfg.get("voice_lufs")},
        },
    )


def _inputs_timeline(ctx):
    return (
        [
            _storyboard_path(ctx),
            ctx.work / "voices" / "manifest.json",
            ctx.root / "config.yaml",
        ],
        {"render": ctx.cfg.get("render")},
    )


def _inputs_mix(ctx):
    sb = _storyboard_optional(ctx)
    paths = [
        ctx.work / "timeline.json",
        ctx.work / "voices" / "manifest.json",
        _storyboard_path(ctx),
        ctx.root / "config.yaml",
    ]
    music = _music_layer(sb)
    if music is not None:
        track = music.get("track")
        if isinstance(track, str) and track:
            paths.append(_root_path(ctx, track))
    return paths, {"mix": ctx.cfg.get("mix")}


def _inputs_render(ctx):
    sb = _storyboard_optional(ctx)
    paths = [
        ctx.work / "timeline.json",
        ctx.work / "subs.json",
        ctx.work / "mix.wav",
        _storyboard_path(ctx),
        ctx.root / "config.yaml",
    ]
    paths.extend(_asset_paths(ctx, sb))
    return paths, {"render": ctx.cfg.get("render")}


def _inputs_qa(ctx):
    return (
        [
            ctx.out / "video.mp4",
            ctx.work / "subs.json",
            ctx.work / "loudness.json",
            ctx.work / "timeline.json",
            ctx.root / "config.yaml",
        ],
        {
            "qa": ctx.cfg.get("qa"),
            "render": ctx.cfg.get("render"),
            "mix": ctx.cfg.get("mix"),
        },
    )


def _outputs_validate(ctx):
    return [ctx.work / "validate.json"]


def _outputs_voices(ctx):
    outputs = [ctx.work / "voices" / "manifest.json"]
    for scene_id, _layer, _scene in _narrated_scenes(_storyboard_optional(ctx)):
        outputs.append(ctx.work / "voices" / (scene_id + ".wav"))
    return outputs


def _outputs_timeline(ctx):
    return [
        ctx.work / "timeline.json",
        ctx.work / "subs.json",
        ctx.out / "legendas.srt",
    ]


def _outputs_mix(ctx):
    outputs = [
        ctx.work / "mix.wav",
        ctx.work / "loudness.json",
        ctx.work / "bed.wav",
    ]
    for scene_id, _layer, _scene in _narrated_scenes(_storyboard_optional(ctx)):
        outputs.append(ctx.work / "voices" / (scene_id + ".fit.wav"))
    return outputs


def _outputs_render(ctx):
    return [ctx.out / "video.mp4"]


def _outputs_qa(ctx):
    return [ctx.out / "qa.json"]


def steps_factory():
    return [
        Step(
            "validate",
            "Valida storyboard.yaml (esquema, assets, licencas de musica).",
            _inputs_validate,
            _outputs_validate,
            _run_validate,
            [],
        ),
        Step(
            "voices",
            "Sintetiza a narracao de cada cena (cache por hash).",
            _inputs_voices,
            _outputs_voices,
            _run_voices,
            ["validate"],
        ),
        Step(
            "timeline",
            "Resolve duracoes e ancoras e gera a linha do tempo e as legendas.",
            _inputs_timeline,
            _outputs_timeline,
            _run_timeline,
            ["voices"],
        ),
        Step(
            "mix",
            "Mistura narracao e trilha com ducking e normaliza o loudness.",
            _inputs_mix,
            _outputs_mix,
            _run_mix,
            ["timeline"],
        ),
        Step(
            "render",
            "Renderiza a composicao Storyboard e muxa o audio final.",
            _inputs_render,
            _outputs_render,
            _run_render,
            ["mix"],
        ),
        Step(
            "qa",
            "Verifica loudness, legendas e consistencia do resultado.",
            _inputs_qa,
            _outputs_qa,
            _run_qa,
            ["render"],
        ),
    ]


FILES = {
    "agent_writes": ["storyboard.yaml", "config.yaml", "voices/<cena>.wav"],
    "generated": ["work/", "out/video.mp4", "out/legendas.srt", "out/qa.json"],
}

if "storyboard" not in WORKFLOWS:
    register_workflow(
        "storyboard",
        "Video por cenas (clipes, cards, narracao, trilha) a partir de um storyboard.yaml.",
        steps_factory,
        FILES,
    )
