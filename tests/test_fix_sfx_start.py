"""Contrato fx-t2: ``sfx.start`` respeitado (M2) e ``clip.out_s`` honesto (L3).

Decisoes de contrato desta lane (fase 1, so teste):

- ``sfx.start`` e relativo ao inicio da cena, em segundos:
  ``layer.start == scene.start + sfx.start``. Sem ``start`` numerico, a camada
  continua comecando em ``scene.start``.
- ``sfx.start`` fora da cena e **erro** de ``validate_storyboard`` com o codigo
  ``SFX_START``; o limite superior e ``scene.duration.fixed_s`` (inicio igual ao
  fim nao toca nada, entao tambem e erro). Para cenas ``from: narration`` a
  duracao nao existe no validate, mas ``start`` negativo continua sendo erro.
- ``clip.out_s`` e aceito pelo schema, mas ignorado em runtime; o validate
  apenas avisa (``warn``) com ``CLIP_OUT_S_UNSUPPORTED``.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_HAS_FFMPEG = (
    shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
)

_UNSET = object()


# ------------------------------------------------------------------ helpers


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


def _clip(**overrides):
    layer = {
        "type": "clip",
        "file": "assets/clip.mp4",
        "in_s": 0,
        "fit": "cover",
    }
    layer.update(overrides)
    return layer


def _scene(scene_id="S1", fixed_s=2.0, layers=None):
    return {
        "id": scene_id,
        "duration": {"fixed_s": fixed_s},
        "layers": list(layers or []),
    }


def _sb(*scenes):
    return {
        "version": 1,
        "canvas": {"w": 320, "h": 180, "fps": 30},
        "scenes": list(scenes),
    }


def _ctx(root):
    from forja import steps

    return steps.Ctx(
        root=Path(root),
        cfg={},
        work=Path(root) / "work",
        out=Path(root) / "out",
        env={},
        log=lambda _message: None,
        dry_run=False,
    )


def _issues(issues, code):
    return [issue for issue in issues if issue.get("code") == code]


def _has(issues, code, level=None):
    return any(
        issue.get("code") == code
        and (level is None or issue.get("level") == level)
        for issue in issues
    )


def _errors(issues):
    return [issue for issue in issues if issue.get("level") == "error"]


def _ffmpeg(cmd) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail("ffmpeg falhou:\n" + (result.stderr or "")[-1500:])


def _make_sfx(path: Path, frequency=900, duration=0.5) -> Path:
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


def _tone_ratio(samples, rate, start_s, end_s, frequency=900.0, half_band=40.0):
    """Fracao da energia espectral na banda do tom, dentro da janela dada."""
    import numpy as np

    start = int(round(start_s * rate))
    end = int(round(end_s * rate))
    chunk = samples[start:end]
    if chunk.size < 16:
        return 0.0
    spectrum = np.abs(np.fft.rfft(chunk * np.hanning(chunk.size)))
    freqs = np.fft.rfftfreq(chunk.size, d=1.0 / float(rate))
    band = (freqs >= frequency - half_band) & (freqs <= frequency + half_band)
    total = float(np.sum(spectrum**2))
    if total <= 0.0:
        return 0.0
    return float(np.sum(spectrum[band] ** 2)) / total


# --------------------------------------------------- M2: resolve_timeline


def test_resolve_timeline_sfx_start_is_relative_to_scene_start():
    from forja import storyboard

    sb = _sb(_scene("S1", 2.0, [_sfx(start=1.0)]))
    timeline = storyboard.resolve_timeline(sb, {})
    scene = timeline["scenes"][0]
    layer = scene["layers"][0]

    assert layer["type"] == "sfx"
    assert layer["start"] == pytest.approx(scene["start"] + 1.0)


def test_resolve_timeline_sfx_start_accumulates_scene_start():
    from forja import storyboard

    sb = _sb(
        _scene("S1", 2.0, []),
        _scene("S2", 2.0, [_sfx(start=0.25)]),
    )
    timeline = storyboard.resolve_timeline(sb, {})
    second = timeline["scenes"][1]
    layer = second["layers"][0]

    assert second["start"] == pytest.approx(2.0)
    assert layer["start"] == pytest.approx(2.25)


def test_resolve_timeline_sfx_without_start_uses_scene_start():
    from forja import storyboard

    sb = _sb(_scene("S1", 2.0, [_sfx()]))
    timeline = storyboard.resolve_timeline(sb, {})
    scene = timeline["scenes"][0]
    layer = scene["layers"][0]

    assert layer["start"] == pytest.approx(scene["start"])


def test_resolve_timeline_enter_at_s_still_applies_to_non_sfx():
    from forja import storyboard

    card = {"type": "card", "asset": "assets/card.png", "enter": {"at_s": 0.5}}
    sb = _sb(_scene("S1", 2.0, [card]))
    timeline = storyboard.resolve_timeline(sb, {})
    scene = timeline["scenes"][0]
    layer = scene["layers"][0]

    assert layer["start"] == pytest.approx(scene["start"] + 0.5)


def test_audio_plan_uses_resolved_sfx_start(tmp_path):
    from forja import storyboard
    from forja.workflows import storyboard as workflow

    root = Path(tmp_path)
    asset = root / "assets" / "sfx.wav"
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(b"RIFF")

    sb = _sb(_scene("S1", 2.0, [_sfx(start=1.0)]))
    timeline = storyboard.resolve_timeline(sb, {})
    plan = workflow._audio_plan(_ctx(root), sb, timeline, 2.0)

    sfx_items = [item for item in plan if item.get("kind") == "sfx"]
    assert len(sfx_items) == 1
    assert sfx_items[0]["start"] == pytest.approx(1.0)
    assert sfx_items[0]["duration"] == pytest.approx(0.5)


# ------------------------------------------------------ M2: validacao


def test_validate_rejects_sfx_start_beyond_scene():
    from forja import storyboard

    sb = _sb(_scene("S1", 2.0, [_sfx(start=2.5, id="boom")]))
    issues = storyboard.validate_storyboard(sb)
    matched = _issues(issues, "SFX_START")

    assert matched, issues
    assert matched[0]["level"] == "error"
    assert matched[0]["id"] == "boom"
    assert "start" in matched[0]["msg"].lower()


def test_validate_rejects_sfx_start_at_scene_end():
    from forja import storyboard

    sb = _sb(_scene("S1", 2.0, [_sfx(start=2.0)]))
    assert _has(storyboard.validate_storyboard(sb), "SFX_START", "error")


def test_validate_accepts_sfx_start_inside_scene():
    from forja import storyboard

    for start in (0.0, 0.5, 1.0):
        sb = _sb(_scene("S1", 2.0, [_sfx(start=start)]))
        issues = storyboard.validate_storyboard(sb)
        assert not _has(issues, "SFX_START"), (start, issues)
        assert not _errors(issues), (start, issues)


def test_validate_sfx_without_license_still_errors():
    from forja import storyboard

    layer = _sfx(start=1.0)
    layer.pop("license")
    issues = storyboard.validate_storyboard(_sb(_scene("S1", 2.0, [layer])))

    assert _has(issues, "SFX_NO_LICENSE", "error")


# ------------------------------------------------------- L3: clip.out_s


def test_validate_clip_out_s_warns_unsupported():
    from forja import storyboard

    layer = _clip(id="corte", out_s=1.5)
    issues = storyboard.validate_storyboard(_sb(_scene("S1", 2.0, [layer])))
    matched = _issues(issues, "CLIP_OUT_S_UNSUPPORTED")

    assert len(matched) == 1, issues
    issue = matched[0]
    assert issue["level"] == "warn"
    assert issue["id"] == "corte"
    message = issue["msg"].lower()
    assert "ignorado" in message
    assert "cena" in message
    assert not _errors(issues), issues


def test_validate_clip_without_out_s_has_no_out_s_issue():
    from forja import storyboard

    layer = _clip(in_s=0.5)
    issues = storyboard.validate_storyboard(_sb(_scene("S1", 2.0, [layer])))

    assert not _has(issues, "CLIP_OUT_S_UNSUPPORTED"), issues
    assert not _errors(issues), issues


def test_validate_out_s_only_applies_to_clip():
    from forja import storyboard

    card = {"type": "card", "asset": "assets/card.png", "out_s": 1.0}
    issues = storyboard.validate_storyboard(_sb(_scene("S1", 2.0, [card])))

    assert not _has(issues, "CLIP_OUT_S_UNSUPPORTED"), issues


# ------------------------------------------- M2/M3: bed real com ffmpeg


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_mix_bed_plays_sfx_at_start_seconds(tmp_path):
    """Prova por medicao do WAV que o sfx toca em 1.0-1.5 s, nao em 0.0-0.4 s."""
    from forja import storyboard
    from forja.workflows import storyboard as workflow

    root = Path(tmp_path)
    _make_sfx(root / "assets" / "sfx.wav", frequency=900, duration=0.5)

    sb = _sb(_scene("S1", 2.0, [_sfx(start=1.0)]))
    timeline = storyboard.resolve_timeline(sb, {})
    assert timeline["total_s"] == pytest.approx(2.0)

    bed = root / "work" / "bed.wav"
    workflow._build_bed(_ctx(root), sb, timeline, 2.0, bed)
    assert bed.is_file()

    rate, samples = _read_mono(bed)
    assert rate == 48000
    assert samples.size == pytest.approx(2.0 * rate, abs=0.05 * rate)

    # Ha som (900 Hz) na janela do start resolvido...
    assert _rms(samples[int(1.0 * rate) : int(1.45 * rate)]) > 0.02
    assert _tone_ratio(samples, rate, 1.0, 1.45) > 0.5
    # ...e silencio no inicio da cena.
    assert _rms(samples[int(0.05 * rate) : int(0.4 * rate)]) < 0.005
    assert _tone_ratio(samples, rate, 0.05, 0.4) < 0.1
