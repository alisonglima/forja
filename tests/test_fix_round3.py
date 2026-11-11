"""Contrato da rodada 3 da auditoria (M1, M2, B3, B5).

Esta lane escreve apenas o contrato: os testes abaixo descrevem o comportamento
corrigido e devem falhar no codigo atual. Nenhum teste edita ``forja/``.

- M1: o plano de audio e o bed respeitam o fim resolvido da camada ``sfx``
  (``exit``/``hold_s``); ``duration`` menor que o ``exit`` continua vencendo e
  um ``sfx`` sem ``exit`` nao vaza para a cena seguinte.
- M2: ``sfx`` com ``enter.anchor: scene_end`` e offset zero continua rejeitado,
  mas o hint fala do ``enter`` resolvido no fim da cena e sugere ``offset_s``
  negativo (sem mandar usar ``enter.anchor``). O hint de ``sfx.start`` fica.
- B3: o passo ``timeline`` recusa ids de cena duplicados antes de transcrever
  ou gravar ``timeline.json``.
- B5: ``validate_storyboard`` trata ``sfx.start`` nao finito como ``SFX_START``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import wave
from pathlib import Path

import pytest

_HAS_FFMPEG = (
    shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
)

_UNSET = object()


# --------------------------------------------------------------------- apoio


def _sfx(start=_UNSET, **overrides):
    layer = {
        "type": "sfx",
        "asset": "assets/sfx.wav",
        "duration": 0.5,
        "license": {"kind": "cc0"},
    }
    if start is not _UNSET:
        layer["start"] = start
    layer.update(overrides)
    return layer


def _card(**overrides):
    layer = {"type": "card", "asset": "assets/card.png"}
    layer.update(overrides)
    return layer


def _scene(scene_id="s1", duration=None, layers=None):
    return {
        "id": scene_id,
        "duration": duration if duration is not None else {"fixed_s": 2.0},
        "layers": list(layers or []),
    }


def _sb(*scenes):
    return {
        "version": 1,
        "canvas": {"w": 320, "h": 180, "fps": 30},
        "scenes": list(scenes),
    }


def _issues(issues, code):
    return [issue for issue in issues if issue.get("code") == code]


def _errors(issues):
    return [issue for issue in issues if issue.get("level") == "error"]


def _make_ctx(root: Path):
    from forja import steps
    from forja.project import Project

    project = Project(root)
    return steps.Ctx(
        root=Path(root),
        cfg=project.load_config(),
        work=project.work,
        out=project.out,
        env={},
        log=lambda _message: None,
        dry_run=False,
    )


def _write_storyboard(root: Path, storyboard: dict) -> None:
    import yaml

    (Path(root) / "storyboard.yaml").write_text(
        yaml.safe_dump(storyboard, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _new_storyboard_project(tmp_path: Path, storyboard: dict, name: str = "p") -> Path:
    from forja import project

    root = Path(tmp_path) / name
    project.scaffold(root, "demo", workflow="storyboard")
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "card.png").write_bytes(b"png")
    (assets / "sfx.wav").write_bytes(b"RIFF")
    _write_storyboard(root, storyboard)
    return root


def _write_voice_cache(
    root: Path,
    durations=None,
    text: str = "um dois tres",
) -> None:
    """Cria WAVs de narracao e o manifesto lido pelo passo ``timeline``."""
    from forja import tts

    voices = Path(root) / "work" / "voices"
    voices.mkdir(parents=True, exist_ok=True)
    durations = durations if isinstance(durations, dict) else {"s1": 3.0}
    manifest = {}
    for scene_id, duration in durations.items():
        wav_path = voices / (str(scene_id) + ".wav")
        wav_path.write_bytes(tts.mock_wav(text))
        with wave.open(str(wav_path), "rb") as handle:
            real_duration = handle.getnframes() / float(handle.getframerate())
        manifest[str(scene_id)] = {
            "wav": "work/voices/%s.wav" % scene_id,
            "duration": float(duration if duration is not None else real_duration),
        }
    _write_json(voices / "manifest.json", manifest)


def _fake_transcript(words):
    return {
        "segments": [
            {
                "words": [
                    {"word": word, "start": start, "end": start + 0.1}
                    for word, start in words
                ]
            }
        ]
    }


def _workflow_steps():
    from forja import workflows
    from forja.workflows import storyboard as _storyboard  # noqa: F401  (registra)

    return workflows.get_workflow("storyboard").steps_factory()


def _step(root: Path, name: str):
    return next(step for step in _workflow_steps() if step.name == name)


def _narration(text: str) -> dict:
    return {"type": "narration", "text": text, "lang": "pt-BR"}


def _ffmpeg(cmd) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail("ffmpeg falhou:\n" + (result.stderr or "")[-1500:])


def _make_sfx(path: Path, frequency=700, duration=5.0) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=%d:duration=%s:sample_rate=48000"
            % (frequency, duration),
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(path),
        ]
    )
    return path


def _read_mono(path: Path):
    from scipy.io import wavfile

    rate, data = wavfile.read(str(path))
    samples = data.astype("float64")
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    return int(rate), samples / 32768.0


def _rms(samples) -> float:
    import numpy as np

    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples))))


def _sfx_item(root: Path, sb: dict, timeline: dict) -> dict:
    from forja.workflows import storyboard as workflow

    plan = workflow._audio_plan(_make_ctx(root), sb, timeline, timeline["total_s"])
    items = [item for item in plan if item.get("kind") == "sfx"]
    assert len(items) == 1, plan
    return items[0]


def _bed(root: Path, sb: dict, timeline: dict, name: str):
    from forja.workflows import storyboard as workflow

    bed = Path(root) / "work" / name
    workflow._build_bed(_make_ctx(root), sb, timeline, timeline["total_s"], bed)
    assert bed.is_file()
    rate, samples = _read_mono(bed)
    assert rate == 48000
    assert samples.size == pytest.approx(
        float(timeline["total_s"]) * rate, abs=0.05 * rate
    )
    return rate, samples


# ------------------------------------------------ M1: fim resolvido no plano


def test_audio_plan_sfx_exit_caps_resolved_end(tmp_path):
    from forja import storyboard

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 2.0},
            [
                _sfx(
                    duration=5.0,
                    enter={"anchor": "scene_start"},
                    exit={"anchor": "at_s", "at_s": 1.0},
                )
            ],
        )
    )
    root = _new_storyboard_project(tmp_path, sb)
    timeline = storyboard.resolve_timeline(sb, {})
    layer = timeline["scenes"][0]["layers"][0]
    assert layer["start"] == pytest.approx(0.0)
    assert layer["end"] == pytest.approx(1.0)

    item = _sfx_item(root, sb, timeline)
    assert item["start"] == pytest.approx(0.0)
    assert item["duration"] == pytest.approx(1.0)


def test_audio_plan_sfx_exit_by_word_caps_resolved_end(tmp_path):
    from forja import storyboard

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 2.0},
            [
                _sfx(
                    duration=5.0,
                    enter={"anchor": "scene_start"},
                    exit={"anchor": "word", "word": "dois"},
                )
            ],
        )
    )
    root = _new_storyboard_project(tmp_path, sb)
    words = {"s1": [{"word": "dois", "start": 0.8, "end": 1.0}]}
    timeline = storyboard.resolve_timeline(sb, {}, words=words)
    layer = timeline["scenes"][0]["layers"][0]
    assert layer["end"] == pytest.approx(0.8)

    item = _sfx_item(root, sb, timeline)
    assert item["duration"] == pytest.approx(0.8)


def test_audio_plan_sfx_exit_earlier_than_duration_wins(tmp_path):
    from forja import storyboard

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 2.0},
            [
                _sfx(
                    duration=0.4,
                    enter={"anchor": "scene_start"},
                    exit={"anchor": "at_s", "at_s": 0.1},
                )
            ],
        )
    )
    root = _new_storyboard_project(tmp_path, sb)
    timeline = storyboard.resolve_timeline(sb, {})
    layer = timeline["scenes"][0]["layers"][0]
    assert layer["end"] == pytest.approx(0.1)

    item = _sfx_item(root, sb, timeline)
    assert item["duration"] == pytest.approx(0.1)


def test_audio_plan_sfx_duration_shorter_than_exit_wins(tmp_path):
    from forja import storyboard

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 2.0},
            [
                _sfx(
                    duration=0.4,
                    enter={"anchor": "scene_start"},
                    exit={"anchor": "at_s", "at_s": 1.0},
                )
            ],
        )
    )
    root = _new_storyboard_project(tmp_path, sb)
    timeline = storyboard.resolve_timeline(sb, {})
    layer = timeline["scenes"][0]["layers"][0]
    assert layer["end"] == pytest.approx(1.0)

    item = _sfx_item(root, sb, timeline)
    assert item["duration"] == pytest.approx(0.4)


def test_audio_plan_sfx_hold_s_caps_resolved_end(tmp_path):
    from forja import storyboard

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 2.0},
            [
                _sfx(
                    duration=5.0,
                    enter={"anchor": "scene_start"},
                    hold_s=0.5,
                )
            ],
        )
    )
    root = _new_storyboard_project(tmp_path, sb)
    timeline = storyboard.resolve_timeline(sb, {})
    layer = timeline["scenes"][0]["layers"][0]
    assert layer["end"] == pytest.approx(0.5)

    item = _sfx_item(root, sb, timeline)
    assert item["duration"] == pytest.approx(0.5)


def test_audio_plan_sfx_without_exit_stops_at_scene_end(tmp_path):
    from forja import storyboard

    layer = _sfx(enter={"anchor": "scene_start"})
    layer.pop("duration")
    sb = _sb(
        _scene("s1", {"fixed_s": 2.0}, [layer]),
        _scene("s2", {"fixed_s": 2.0}, []),
    )
    root = _new_storyboard_project(tmp_path, sb)
    timeline = storyboard.resolve_timeline(sb, {})
    resolved = timeline["scenes"][0]["layers"][0]
    assert resolved["end"] == pytest.approx(2.0)
    assert timeline["total_s"] == pytest.approx(4.0)

    item = _sfx_item(root, sb, timeline)
    assert item["duration"] == pytest.approx(2.0)


# -------------------------------------------- M1: corte comprovado no bed


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_audio_bed_sfx_exit_cuts_tone(tmp_path):
    from forja import storyboard

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 2.0},
            [
                _sfx(
                    duration=5.0,
                    enter={"anchor": "scene_start"},
                    exit={"anchor": "at_s", "at_s": 1.0},
                )
            ],
        )
    )
    root = _new_storyboard_project(tmp_path, sb)
    _make_sfx(root / "assets" / "sfx.wav", frequency=700, duration=5.0)
    timeline = storyboard.resolve_timeline(sb, {})

    rate, samples = _bed(root, sb, timeline, "bed-exit.wav")
    assert _rms(samples[int(0.1 * rate) : int(0.9 * rate)]) > 0.05
    assert _rms(samples[int(1.1 * rate) : int(1.9 * rate)]) < 0.005


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_audio_bed_sfx_earlier_exit_cuts_shorter_duration(tmp_path):
    from forja import storyboard

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 2.0},
            [
                _sfx(
                    duration=0.4,
                    enter={"anchor": "scene_start"},
                    exit={"anchor": "at_s", "at_s": 0.1},
                )
            ],
        )
    )
    root = _new_storyboard_project(tmp_path, sb)
    _make_sfx(root / "assets" / "sfx.wav", frequency=700, duration=5.0)
    timeline = storyboard.resolve_timeline(sb, {})

    rate, samples = _bed(root, sb, timeline, "bed-exit-curto.wav")
    assert _rms(samples[int(0.02 * rate) : int(0.08 * rate)]) > 0.05
    assert _rms(samples[int(0.25 * rate) : int(1.9 * rate)]) < 0.005


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_audio_bed_sfx_duration_shorter_than_exit_wins(tmp_path):
    from forja import storyboard

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 2.0},
            [
                _sfx(
                    duration=0.4,
                    enter={"anchor": "scene_start"},
                    exit={"anchor": "at_s", "at_s": 1.0},
                )
            ],
        )
    )
    root = _new_storyboard_project(tmp_path, sb)
    _make_sfx(root / "assets" / "sfx.wav", frequency=700, duration=5.0)
    timeline = storyboard.resolve_timeline(sb, {})

    rate, samples = _bed(root, sb, timeline, "bed-duration.wav")
    assert _rms(samples[int(0.05 * rate) : int(0.35 * rate)]) > 0.05
    assert _rms(samples[int(0.55 * rate) : int(1.9 * rate)]) < 0.005


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_audio_bed_sfx_hold_s_cuts_tone(tmp_path):
    from forja import storyboard

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 2.0},
            [
                _sfx(
                    duration=5.0,
                    enter={"anchor": "scene_start"},
                    hold_s=0.5,
                )
            ],
        )
    )
    root = _new_storyboard_project(tmp_path, sb)
    _make_sfx(root / "assets" / "sfx.wav", frequency=700, duration=5.0)
    timeline = storyboard.resolve_timeline(sb, {})

    rate, samples = _bed(root, sb, timeline, "bed-hold.wav")
    assert _rms(samples[int(0.05 * rate) : int(0.45 * rate)]) > 0.05
    assert _rms(samples[int(0.65 * rate) : int(1.9 * rate)]) < 0.005


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_audio_bed_sfx_without_exit_does_not_bleed_to_next_scene(tmp_path):
    from forja import storyboard

    layer = _sfx(enter={"anchor": "scene_start"})
    layer.pop("duration")
    sb = _sb(
        _scene("s1", {"fixed_s": 2.0}, [layer]),
        _scene("s2", {"fixed_s": 2.0}, []),
    )
    root = _new_storyboard_project(tmp_path, sb)
    _make_sfx(root / "assets" / "sfx.wav", frequency=700, duration=5.0)
    timeline = storyboard.resolve_timeline(sb, {})

    rate, samples = _bed(root, sb, timeline, "bed-sem-exit.wav")
    assert _rms(samples[int(0.1 * rate) : int(1.9 * rate)]) > 0.05
    assert _rms(samples[int(2.1 * rate) : int(3.9 * rate)]) < 0.005


# ------------------------------------------------- M2: hint de enter/scene_end


def _scene_end_storyboard(offset=None):
    enter = {"anchor": "scene_end"}
    if offset is not None:
        enter["offset_s"] = offset
    return _sb(_scene("s1", {"fixed_s": 2.0}, [_sfx(enter=enter)]))


def test_timeline_sfx_enter_scene_end_hint_distinguishes_enter(tmp_path):
    from forja import errors

    root = _new_storyboard_project(tmp_path, _scene_end_storyboard())
    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "CONFIG_INVALID"
    details = error.details or {}
    assert details.get("scene") == "s1"
    assert float(details.get("start")) == pytest.approx(2.0)
    assert float(details.get("scene_start")) == pytest.approx(0.0)
    assert float(details.get("scene_end")) == pytest.approx(2.0)

    hint = (error.hint or "").lower()
    assert hint
    assert "enter" in hint or "ancora" in hint or "âncora" in hint
    assert "offset_s" in hint
    assert "negativ" in hint or "outra ancora" in hint or "outra âncora" in hint
    assert "ou use enter.anchor" not in hint
    assert not (root / "work" / "timeline.json").exists()


def test_timeline_sfx_start_outside_scene_keeps_start_hint(tmp_path):
    from forja import errors

    sb = _sb(_scene("s1", {"fixed_s": 2.0}, [_sfx(start=2.5)]))
    root = _new_storyboard_project(tmp_path, sb)
    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "CONFIG_INVALID"
    hint = (error.hint or "").lower()
    assert "sfx.start" in hint
    assert "cena" in hint
    assert not (root / "work" / "timeline.json").exists()


def test_timeline_sfx_enter_scene_end_negative_offset_still_works(tmp_path):
    root = _new_storyboard_project(tmp_path, _scene_end_storyboard(offset=-0.5))

    _step(root, "timeline").run(_make_ctx(root))

    timeline = json.loads(
        (root / "work" / "timeline.json").read_text(encoding="utf-8")
    )
    layer = timeline["scenes"][0]["layers"][0]
    assert layer["type"] == "sfx"
    assert layer["start"] == pytest.approx(1.5)


# ------------------------------------------------------- B3: ids duplicados


def _duplicate_id_storyboard():
    return _sb(
        _scene(
            "s1",
            {"fixed_s": 2.0},
            [
                _narration("um dois"),
                _card(enter={"anchor": "word", "word": "dois"}),
            ],
        ),
        _scene(
            "s1",
            {"fixed_s": 2.0},
            [
                _narration("um banana"),
                _card(enter={"anchor": "word", "word": "dois"}),
            ],
        ),
    )


def test_timeline_duplicate_scene_ids_fail_before_transcribing(monkeypatch, tmp_path):
    from forja import errors
    from forja.workflows import storyboard as workflow

    root = _new_storyboard_project(tmp_path, _duplicate_id_storyboard())
    _write_voice_cache(root, {"s1": 3.0})
    calls = []

    def fake_transcribe(wav, cfg, model_dir):
        calls.append(str(wav))
        return _fake_transcript([("um", 0.0), ("dois", 1.0)])

    monkeypatch.setattr(workflow.transcribe, "run_transcribe", fake_transcribe)

    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "CONFIG_INVALID"
    details = error.details or {}
    assert details.get("scene") == "s1"
    hint = (error.hint or "").lower()
    assert hint
    assert any(token in hint for token in ("id", "duplic", "unic", "ún"))
    assert calls == []
    assert not (root / "work" / "timeline.json").exists()


def test_timeline_distinct_scene_ids_still_write_timeline(tmp_path):
    from forja.workflows import storyboard as workflow

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 2.0},
            [_card(enter={"anchor": "scene_start", "offset_s": 0.5})],
        ),
        _scene(
            "s2",
            {"fixed_s": 2.0},
            [_card(enter={"anchor": "scene_start", "offset_s": 0.5})],
        ),
    )
    root = _new_storyboard_project(tmp_path, sb)

    _step(root, "timeline").run(_make_ctx(root))

    timeline = json.loads(
        (root / "work" / "timeline.json").read_text(encoding="utf-8")
    )
    assert [scene["id"] for scene in timeline["scenes"]] == ["s1", "s2"]
    assert timeline["scenes"][1]["layers"][0]["start"] == pytest.approx(2.5)


# ------------------------------------------------ B5: sfx.start nao finito


@pytest.mark.parametrize(
    "start",
    [float("nan"), float("inf"), float("-inf")],
    ids=["nan", "inf", "menos_inf"],
)
def test_validate_sfx_start_non_finite_is_error(start):
    from forja import storyboard

    sb = _sb(_scene("s1", {"fixed_s": 2.0}, [_sfx(start=start)]))
    issues = storyboard.validate_storyboard(sb)
    matched = _issues(issues, "SFX_START")

    assert matched, issues
    assert matched[0]["level"] == "error", matched[0]
    assert _errors(issues), issues


@pytest.mark.parametrize("start", [0, 0.5, 1.0])
def test_validate_sfx_finite_start_still_valid(start):
    from forja import storyboard

    sb = _sb(_scene("s1", {"fixed_s": 2.0}, [_sfx(start=start)]))
    issues = storyboard.validate_storyboard(sb)

    assert not _issues(issues, "SFX_START"), issues
    assert not _errors(issues), issues
