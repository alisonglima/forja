from __future__ import annotations

import json
import urllib.error
import urllib.request
import wave
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from .. import cues as cues_mod
from .. import ids
from .. import media, mixlib, probe, qa, render, schedule, subs, transcribe, tts
from ..errors import ForjaError
from ..steps import Step
from . import WORKFLOWS, register_workflow


# --------------------------------------------------------------------- apoio


def _read_json(path, default=None):
    path = Path(path)
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ForjaError(
            "MISSING_INPUT",
            "arquivo gerado ilegivel: %s" % path,
            hint="apague o arquivo e rode o passo de novo (ou use --force)",
            details={"path": str(path), "error": str(exc)},
        ) from exc


def _write_json(path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _root_path(ctx, value) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ctx.root / path


def _lower_thirds(ctx):
    data = _read_json(ctx.root / "lower_thirds.json", [])
    return data if isinstance(data, list) else []


def _wav_duration(path) -> float:
    with wave.open(str(path), "rb") as wav:
        rate = wav.getframerate()
        return wav.getnframes() / float(rate) if rate else 0.0


def _cue_ids_from_cues(ctx):
    data = _read_json(ctx.root / "cues.json", [])
    if not isinstance(data, list):
        return []
    return [str(cue.get("id")) for cue in data if isinstance(cue, dict)]


def _cue_ids_from_plan(ctx):
    data = _read_json(ctx.work / "plan.json", {})
    entries = data.get("cues") if isinstance(data, dict) else None
    if isinstance(entries, list) and entries:
        return [str(entry.get("id")) for entry in entries]
    return _cue_ids_from_cues(ctx)


# -------------------------------------------------------------------- HTTP


class _HTTPStatusError(RuntimeError):
    """Erro HTTP com o atributo ``status`` que ``tts.synthesize`` consulta."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = int(status)


def _http_post(url, headers, body) -> dict:
    """POST JSON por HTTPS; erro HTTP vira excecao com ``status``."""
    target = str(url)
    if not target.startswith("https://"):
        raise ValueError("apenas URLs https sao permitidas")
    if isinstance(body, (bytes, bytearray)):
        payload = bytes(body)
    else:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        target,
        data=payload,
        headers=dict(headers or {}),
        method="POST",
    )
    try:
        # A URL ja foi validada como https:// acima; o destino vem do provedor configurado.
        with urllib.request.urlopen(  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
            request, timeout=120
        ) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise _HTTPStatusError(exc.code, "HTTP %s" % exc.code) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise _HTTPStatusError(0, "falha de rede: %s" % (reason,)) from exc
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


# ------------------------------------------------------------------- passos


def _run_clip(ctx):
    input_cfg = ctx.cfg.get("input") or {}
    video = _root_path(ctx, input_cfg.get("video", "input/source.mp4"))
    if not video.is_file():
        raise ForjaError(
            "MISSING_INPUT",
            "video de entrada nao encontrado: %s" % video.name,
            details={"path": str(video)},
        )
    clip = ctx.work / "clip.mp4"
    ctx.work.mkdir(parents=True, exist_ok=True)
    media.cut_clip(
        video,
        clip,
        input_cfg.get("start", 0.0),
        input_cfg.get("duration"),
    )
    info = probe.probe_video(clip)
    _write_json(ctx.work / "clip.json", info)
    return {
        "duration": info["duration"],
        "width": info["width"],
        "height": info["height"],
    }


def _run_orig(ctx):
    clip = ctx.work / "clip.mp4"
    out = ctx.work / "orig.wav"
    media.extract_audio(clip, out, sr=48000)
    return {"wav": "work/orig.wav"}


def _run_transcribe(ctx):
    model_dir = ctx.env.get("FORJA_MODEL_DIR")
    if not model_dir:
        model_dir = Path.home() / ".cache" / "forja" / "models"
    data = transcribe.run_transcribe(ctx.work / "orig.wav", ctx.cfg, model_dir)
    _write_json(ctx.work / "transcript.json", data)
    return {
        "language": data.get("language"),
        "segments": len(data.get("segments") or []),
    }


def _run_check(ctx):
    cues = cues_mod.load_cues(ctx.root / "cues.json")
    issues = cues_mod.validate_cues(cues, ctx.cfg)
    summary = qa.summarize(issues)
    _write_json(ctx.work / "check.json", summary)
    if summary["errors"]:
        raise ForjaError(
            "GATE_FAILED",
            "cues.json tem %d erro(s)" % summary["errors"],
            details={"issues": issues},
        )
    return {
        "ok": summary["ok"],
        "errors": summary["errors"],
        "warnings": summary["warnings"],
    }


def _run_voices(ctx):
    cues = cues_mod.load_cues(ctx.root / "cues.json")
    voices_dir = ctx.work / "voices"
    voices_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = ctx.work / "cache" / "tts"
    voice_lufs = (ctx.cfg.get("mix") or {}).get("voice_lufs", -18.0)
    manifest = {}
    for cue in cues:
        cid = ids.require_safe_id(cue.get("id"), "id da cue")
        source = tts.source_for(
            cue,
            ctx.cfg,
            ctx.root,
            cache_dir,
            post=_http_post,
            env=ctx.env,
        )
        target = voices_dir / (cid + ".wav")
        cmd = mixlib.voice_gain_cmd(source, target, voice_lufs)
        # O loudnorm do ffmpeg devolve 192 kHz; fixa a taxa para um WAV legivel.
        cmd = cmd[:-1] + ["-ar", "48000", cmd[-1]]
        media.run_checked(cmd)
        manifest[cid] = {
            "wav": "work/voices/%s.wav" % cid,
            "duration": _wav_duration(target),
        }
    _write_json(voices_dir / "manifest.json", manifest)
    return {"voices": len(manifest)}


def _run_schedule(ctx):
    manifest = _read_json(ctx.work / "voices" / "manifest.json", {})
    cues = cues_mod.load_cues(ctx.root / "cues.json")
    lower_thirds = _lower_thirds(ctx)
    clip_info = _read_json(ctx.work / "clip.json", {})
    total = float(clip_info.get("duration", 0.0))

    durations = {}
    bounds = {}
    for cid, entry in manifest.items():
        wav_path = _root_path(ctx, entry.get("wav", ""))
        durations[cid] = float(entry.get("duration", 0.0))
        sample_rate, samples = wavfile.read(str(wav_path))
        data = np.asarray(samples)
        if data.ndim > 1:
            data = data.mean(axis=1)
        bounds[cid] = schedule.speech_bounds(data, int(sample_rate))

    plan = schedule.plan(cues, durations, ctx.cfg, total, bounds)
    _write_json(ctx.work / "plan.json", plan)

    events = subs.build_subs(plan, cues, lower_thirds, ctx.cfg)
    _write_json(ctx.work / "subs.json", events)

    ctx.out.mkdir(parents=True, exist_ok=True)
    (ctx.out / "legendas.srt").write_text(
        subs.to_srt(events), encoding="utf-8"
    )
    return {
        "cues": len(plan.get("cues") or []),
        "subs": len(events),
    }


def _run_mix(ctx):
    plan = _read_json(ctx.work / "plan.json", {})
    manifest = _read_json(ctx.work / "voices" / "manifest.json", {})
    cues = cues_mod.load_cues(ctx.root / "cues.json")
    roles = {str(cue.get("id")): str(cue.get("role", "speech")) for cue in cues}
    mix_cfg = ctx.cfg.get("mix") or {}
    voices_dir = ctx.work / "voices"
    voices_dir.mkdir(parents=True, exist_ok=True)

    voice_items = []
    duck_intervals = []
    for entry in plan.get("cues") or []:
        cid = str(entry.get("id"))
        voice_entry = manifest.get(cid) or {}
        source = _root_path(ctx, voice_entry.get("wav", ""))
        fit = voices_dir / (cid + ".fit.wav")
        tempo = float(entry.get("tempo", 1.0))
        cmd = media.trim_tempo_cmd(source, fit, tempo)
        # Contrato do passo: o WAV encaixado e sempre 48 kHz mono.
        cmd = cmd[:-1] + ["-ar", "48000", "-ac", "1", cmd[-1]]
        media.run_checked(cmd)

        start = float(entry.get("start", 0.0))
        end = float(entry.get("end", start))
        voice_items.append({"wav": fit, "start": start})
        if roles.get(cid) == "narrator":
            db = float(mix_cfg.get("duck_narrator_db", -20.0))
        else:
            db = float(mix_cfg.get("duck_speech_db", -13.0))
        # `media.assemble_mix` espera dB e aplica `db_to_gain` internamente.
        duck_intervals.append((start, end, db))

    raw = ctx.work / "mix_raw.wav"
    media.assemble_mix(
        ctx.work / "orig.wav",
        voice_items,
        duck_intervals,
        ctx.cfg,
        raw,
    )
    media.normalize_loudness(raw, ctx.work / "mix.wav", ctx.cfg)
    # O gate de QA julga o que sera entregue: mede a SAIDA normalizada, nao a entrada do 2o passe.
    measured = media.measure_loudness(ctx.work / "mix.wav", ctx.cfg)
    loudness = {
        "I": measured.get("input_i"),
        "TP": measured.get("input_tp"),
    }
    _write_json(ctx.work / "loudness.json", loudness)
    return {"voices": len(voice_items), "I": loudness["I"]}


def _run_render(ctx):
    events = _read_json(ctx.work / "subs.json", [])
    lower_thirds = _lower_thirds(ctx)
    clip_info = _read_json(ctx.work / "clip.json", {})
    total = float(clip_info.get("duration", 0.0))

    props = render.build_props("clip.mp4", total, events, lower_thirds, ctx.cfg)
    template = ctx.env.get("FORJA_REMOTION_DIR")
    if not template:
        template = Path(__file__).resolve().parents[2] / "remotion-template"
    template = Path(template)
    entry = template / "src" / "index.jsx"
    rendered = ctx.work / "render.mp4"

    media.render_remotion(
        entry,
        props,
        public_dir=ctx.work,
        out=rendered,
        cwd=template,
    )
    ctx.out.mkdir(parents=True, exist_ok=True)
    media.mux(rendered, ctx.work / "mix.wav", ctx.out / "video.mp4")
    return {"video": "out/video.mp4", "duration": total}


def _run_qa(ctx):
    plan = _read_json(ctx.work / "plan.json", {})
    events = _read_json(ctx.work / "subs.json", [])
    loudness = _read_json(ctx.work / "loudness.json", {})
    lower_thirds = _lower_thirds(ctx)

    issues = []
    issues.extend(qa.check_subs(events, ctx.cfg))
    issues.extend(qa.check_overlap(events, lower_thirds, ctx.cfg))
    issues.extend(qa.check_loudness(loudness, ctx.cfg))
    issues.extend(qa.check_schedule(plan))
    summary = qa.summarize(issues)
    _write_json(ctx.out / "qa.json", summary)
    if summary["errors"]:
        raise ForjaError(
            "GATE_FAILED",
            "QA reprovado: %d erro(s)" % summary["errors"],
            details={"issues": issues},
        )
    return {
        "ok": summary["ok"],
        "errors": summary["errors"],
        "warnings": summary["warnings"],
    }


# ------------------------------------------------------- entradas e saidas


def _inputs_clip(ctx):
    input_cfg = ctx.cfg.get("input") or {}
    video = _root_path(ctx, input_cfg.get("video", "input/source.mp4"))
    return [ctx.root / "config.yaml", video], {"input": input_cfg}


def _inputs_orig(ctx):
    return [ctx.work / "clip.mp4"], {}


def _inputs_transcribe(ctx):
    return (
        [ctx.work / "orig.wav", ctx.root / "config.yaml"],
        {"transcribe": ctx.cfg.get("transcribe")},
    )


def _inputs_check(ctx):
    voices = ctx.cfg.get("voices") or {}
    return (
        [ctx.root / "cues.json", ctx.root / "config.yaml"],
        {
            "render": ctx.cfg.get("render"),
            "voices": {"max_tempo": voices.get("max_tempo")},
        },
    )


def _inputs_voices(ctx):
    mix_cfg = ctx.cfg.get("mix") or {}
    paths = [ctx.root / "cues.json", ctx.root / "config.yaml"]
    if str((ctx.cfg.get("voices") or {}).get("provider", "files")) == "files":
        paths.extend(sorted((ctx.root / tts.input_dir(ctx.cfg)).glob("*.wav")))
    return (
        paths,
        {
            "voices": ctx.cfg.get("voices"),
            "mix": {"voice_lufs": mix_cfg.get("voice_lufs")},
        },
    )


def _inputs_schedule(ctx):
    return (
        [
            ctx.work / "voices" / "manifest.json",
            ctx.root / "cues.json",
            ctx.root / "lower_thirds.json",
            ctx.work / "clip.json",
            ctx.root / "config.yaml",
        ],
        {
            "voices": ctx.cfg.get("voices"),
            "render": ctx.cfg.get("render"),
        },
    )


def _inputs_mix(ctx):
    return (
        [
            ctx.work / "plan.json",
            ctx.work / "orig.wav",
            ctx.work / "voices" / "manifest.json",
            ctx.root / "cues.json",
            ctx.root / "config.yaml",
        ],
        {"mix": ctx.cfg.get("mix")},
    )


def _inputs_render(ctx):
    return (
        [
            ctx.work / "mix.wav",
            ctx.work / "subs.json",
            ctx.root / "lower_thirds.json",
            ctx.work / "clip.mp4",
            ctx.work / "clip.json",
            ctx.root / "config.yaml",
        ],
        {"render": ctx.cfg.get("render")},
    )


def _inputs_qa(ctx):
    return (
        [
            ctx.out / "video.mp4",
            ctx.work / "plan.json",
            ctx.work / "subs.json",
            ctx.work / "loudness.json",
            ctx.root / "lower_thirds.json",
            ctx.root / "config.yaml",
        ],
        {
            "qa": ctx.cfg.get("qa"),
            "render": ctx.cfg.get("render"),
            "mix": ctx.cfg.get("mix"),
        },
    )


def _outputs_clip(ctx):
    return [ctx.work / "clip.mp4", ctx.work / "clip.json"]


def _outputs_orig(ctx):
    return [ctx.work / "orig.wav"]


def _outputs_transcribe(ctx):
    return [ctx.work / "transcript.json"]


def _outputs_check(ctx):
    return [ctx.work / "check.json"]


def _outputs_voices(ctx):
    outputs = [ctx.work / "voices" / "manifest.json"]
    for cid in _cue_ids_from_cues(ctx):
        outputs.append(ctx.work / "voices" / (cid + ".wav"))
    return outputs


def _outputs_schedule(ctx):
    return [
        ctx.work / "plan.json",
        ctx.work / "subs.json",
        ctx.out / "legendas.srt",
    ]


def _outputs_mix(ctx):
    outputs = [ctx.work / "mix.wav", ctx.work / "loudness.json"]
    for cid in _cue_ids_from_plan(ctx):
        outputs.append(ctx.work / "voices" / (cid + ".fit.wav"))
    return outputs


def _outputs_render(ctx):
    return [ctx.out / "video.mp4"]


def _outputs_qa(ctx):
    return [ctx.out / "qa.json"]


def steps_factory():
    return [
        Step(
            "clip",
            "Corta o trecho do video de entrada e mede suas propriedades.",
            _inputs_clip,
            _outputs_clip,
            _run_clip,
            [],
        ),
        Step(
            "orig",
            "Extrai o audio original (48 kHz estereo) do trecho.",
            _inputs_orig,
            _outputs_orig,
            _run_orig,
            ["clip"],
        ),
        Step(
            "transcribe",
            "Transcreve o audio original com timestamps por palavra.",
            _inputs_transcribe,
            _outputs_transcribe,
            _run_transcribe,
            ["orig"],
        ),
        Step(
            "check",
            "Valida cues.json (tempo, CPS, linhas, orcamento de duracao).",
            _inputs_check,
            _outputs_check,
            _run_check,
            [],
        ),
        Step(
            "voices",
            "Sintetiza a voz de cada cue (cache por hash).",
            _inputs_voices,
            _outputs_voices,
            _run_voices,
            ["check"],
        ),
        Step(
            "schedule",
            "Planeja encaixe de cada fala no tempo e as legendas.",
            _inputs_schedule,
            _outputs_schedule,
            _run_schedule,
            ["voices"],
        ),
        Step(
            "mix",
            "Mistura vozes e audio original com ducking e normaliza o loudness.",
            _inputs_mix,
            _outputs_mix,
            _run_mix,
            ["schedule", "orig"],
        ),
        Step(
            "render",
            "Renderiza o video com legendas embutidas e muxa o audio final.",
            _inputs_render,
            _outputs_render,
            _run_render,
            ["mix"],
        ),
        Step(
            "qa",
            "Verifica legendas, sobreposicao, loudness e sincronia do resultado.",
            _inputs_qa,
            _outputs_qa,
            _run_qa,
            ["render"],
        ),
    ]


FILES = {
    "agent_writes": ["cues.json", "lower_thirds.json", "config.yaml", "voices/<id>.wav"],
    "generated": ["work/", "out/video.mp4", "out/legendas.srt", "out/qa.json"],
}

if "dub" not in WORKFLOWS:
    register_workflow(
        "dub",
        "Dublagem EN->pt-BR estilo documentario, com legendas embutidas.",
        steps_factory,
        FILES,
    )
