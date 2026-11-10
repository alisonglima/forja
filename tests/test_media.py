"""Contratos de forja.media descritos no DESIGN.md (subprocessos sempre injetados)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pytest


def _fake_run(*, returncode=0, stdout="", stderr="", raises=None, results=None):
    """run= falso: grava argv/kwargs e devolve CompletedProcess (ou levanta erro)."""
    calls = []
    pending = list(results) if results is not None else None

    def run(cmd, **kwargs):
        calls.append({"cmd": cmd, "kwargs": kwargs})
        if raises is not None:
            raise raises
        rc, out, err = returncode, stdout, stderr
        if pending:
            spec = pending.pop(0)
            rc = spec.get("returncode", rc)
            out = spec.get("stdout", out)
            err = spec.get("stderr", err)
        return subprocess.CompletedProcess(cmd, rc, out, err)

    return run, calls


def _write_wav(path, samples, sr):
    from scipy.io import wavfile

    wavfile.write(str(path), int(sr), np.asarray(samples, dtype=np.int16))


def _read_wav(path):
    from scipy.io import wavfile

    return wavfile.read(str(path))


def _const(amplitude, seconds, sr):
    n = int(round(float(seconds) * int(sr)))
    return np.full(n, int(round(float(amplitude) * 32767)), dtype=np.int16)


def _cfg(**mix):
    values = {
        "orig_gain": 1.0,
        "ramp_s": 0.05,
        "target_lufs": -16.0,
        "true_peak": -1.5,
        "lra": 11.0,
    }
    values.update(mix)
    return {"mix": values}


def _joined(cmd):
    return " ".join(str(part) for part in cmd)


def _fps_from(cmd):
    joined = _joined(cmd)
    match = re.search(r"fps=([0-9]+(?:\.[0-9]+)?)(?:/([0-9]+(?:\.[0-9]+)?))?", joined)
    assert match, f"comando sem fps=: {joined}"
    num = float(match.group(1))
    den = float(match.group(2)) if match.group(2) else 1.0
    return num / den


# ---------------------------------------------------------------- run_checked

def test_run_checked_returns_completed_process_on_success():
    from forja import media

    run, calls = _fake_run(stdout="ok")
    result = media.run_checked(["ffmpeg", "-version"], run=run)
    assert result.returncode == 0 and result.stdout == "ok"
    assert calls[0]["cmd"] == ["ffmpeg", "-version"]
    assert calls[0]["kwargs"].get("capture_output") is True
    assert calls[0]["kwargs"].get("text") is True


def test_run_checked_maps_nonzero_exit_to_provider_error():
    from forja import media
    from forja.errors import ForjaError

    run, _ = _fake_run(returncode=3, stderr="boom")
    with pytest.raises(ForjaError) as excinfo:
        media.run_checked(["ffmpeg", "-i", "in.mp4"], run=run)
    err = excinfo.value
    assert err.code == "PROVIDER_ERROR"
    assert "ffmpeg" in err.msg
    assert err.details["cmd"] == "ffmpeg"
    assert err.details["returncode"] == 3
    assert err.details["stderr_tail"] == "boom"


def test_run_checked_keeps_only_the_last_500_chars_of_stderr():
    from forja import media
    from forja.errors import ForjaError

    stderr = "a" * 600 + "TAIL"
    run, _ = _fake_run(returncode=1, stderr=stderr)
    with pytest.raises(ForjaError) as excinfo:
        media.run_checked(["ffmpeg"], run=run)
    assert excinfo.value.details["stderr_tail"] == stderr[-500:]


def test_run_checked_maps_missing_binary_to_missing_prereq():
    from forja import media
    from forja.errors import ForjaError

    run, _ = _fake_run(raises=FileNotFoundError("ffmpeg"))
    with pytest.raises(ForjaError) as excinfo:
        media.run_checked(["ffmpeg"], run=run)
    err = excinfo.value
    assert err.code == "MISSING_PREREQ"
    assert "path" in err.hint.lower() or "instal" in err.hint.lower()


def test_run_checked_names_the_tool_in_the_error_message():
    from forja import media
    from forja.errors import ForjaError

    run, _ = _fake_run(returncode=1, stderr="x")
    with pytest.raises(ForjaError) as excinfo:
        media.run_checked(["remotion", "render"], run=run, what="remotion")
    assert "remotion" in excinfo.value.msg


# -------------------------------------------------------------------- cut_clip

def test_cut_clip_cmd_places_ss_before_input_and_uses_libx264():
    from forja import media

    cmd = media.cut_clip_cmd("in.mp4", "out.mp4", 3.5)
    assert cmd[0] == "ffmpeg" and cmd[-1] == "out.mp4"
    assert cmd[cmd.index("-ss") + 1] == "3.5"
    assert cmd.index("-ss") < cmd.index("-i")
    assert "-t" not in cmd
    assert cmd[cmd.index("-c:v") + 1] == "libx264"
    assert cmd[cmd.index("-preset") + 1] == "fast"
    assert cmd[cmd.index("-crf") + 1] == "18"
    assert cmd[cmd.index("-c:a") + 1] == "aac"


def test_cut_clip_cmd_adds_t_before_input_when_duration_is_given():
    from forja import media

    cmd = media.cut_clip_cmd("in.mp4", "out.mp4", 2.0, 10.5)
    assert cmd[cmd.index("-ss") + 1] == "2.0"
    assert cmd[cmd.index("-t") + 1] == "10.5"
    assert cmd.index("-t") < cmd.index("-i")


def test_cut_clip_runs_the_command_and_returns_output_path(tmp_path):
    from forja import media

    out = tmp_path / "clip.mp4"
    run, calls = _fake_run()
    result = media.cut_clip("in.mp4", out, 1.0, 2.0, run=run)
    assert result == Path(out)
    assert len(calls) == 1
    assert calls[0]["cmd"] == media.cut_clip_cmd("in.mp4", out, 1.0, 2.0)


def test_cut_clip_propagates_ffmpeg_failure(tmp_path):
    from forja import media
    from forja.errors import ForjaError

    run, _ = _fake_run(returncode=1, stderr="cut failed")
    with pytest.raises(ForjaError) as excinfo:
        media.cut_clip("in.mp4", tmp_path / "out.mp4", 0.0, run=run)
    assert excinfo.value.code == "PROVIDER_ERROR"


# ---------------------------------------------------------------- extract_audio

def test_extract_audio_cmd_sets_mono_48k_pcm_s16le():
    from forja import media

    cmd = media.extract_audio_cmd("in.mp4", "out.wav")
    assert cmd[0] == "ffmpeg" and cmd[-1] == "out.wav"
    assert "-vn" in cmd
    assert cmd[cmd.index("-ac") + 1] == "2"
    assert cmd[cmd.index("-ar") + 1] == "48000"
    assert cmd[cmd.index("-c:a") + 1] == "pcm_s16le"


def test_extract_audio_cmd_accepts_custom_sample_rate():
    from forja import media

    cmd = media.extract_audio_cmd("in.mp4", "out.wav", sr=44100)
    assert cmd[cmd.index("-ar") + 1] == "44100"


def test_extract_audio_runs_and_returns_path(tmp_path):
    from forja import media

    out = tmp_path / "orig.wav"
    run, calls = _fake_run()
    result = media.extract_audio("in.mp4", out, sr=44100, run=run)
    assert result == Path(out)
    assert calls[0]["cmd"] == media.extract_audio_cmd("in.mp4", out, sr=44100)


def test_extract_audio_maps_missing_ffmpeg(tmp_path):
    from forja import media
    from forja.errors import ForjaError

    run, _ = _fake_run(raises=FileNotFoundError("ffmpeg"))
    with pytest.raises(ForjaError) as excinfo:
        media.extract_audio("in.mp4", tmp_path / "orig.wav", run=run)
    assert excinfo.value.code == "MISSING_PREREQ"


# ----------------------------------------------------------------- trim_tempo

def test_trim_tempo_cmd_rejects_tempo_below_half():
    from forja import media

    with pytest.raises(ValueError):
        media.trim_tempo_cmd("voz.wav", "out.wav", 0.49)


def test_trim_tempo_cmd_rejects_tempo_above_two():
    from forja import media

    with pytest.raises(ValueError):
        media.trim_tempo_cmd("voz.wav", "out.wav", 2.01)


def test_trim_tempo_cmd_ends_filter_with_atempo():
    from forja import media

    cmd = media.trim_tempo_cmd("voz.wav", "voz_fast.wav", 1.25)
    filt = cmd[cmd.index("-af") + 1]
    assert cmd[0] == "ffmpeg" and cmd[-1] == "voz_fast.wav"
    assert filt.endswith("atempo=1.25")


def test_trim_tempo_cmd_omits_atempo_when_tempo_is_one():
    from forja import media

    cmd = media.trim_tempo_cmd("voz.wav", "out.wav", 1.0)
    assert "atempo" not in cmd[cmd.index("-af") + 1]


def test_trim_tempo_cmd_trims_silence_at_both_ends():
    from forja import media

    cmd = media.trim_tempo_cmd("voz.wav", "out.wav", 1.1)
    filt = cmd[cmd.index("-af") + 1]
    assert "silenceremove" in filt
    assert "areverse" in filt


def test_trim_tempo_cmd_can_skip_silence_trimming():
    from forja import media

    cmd = media.trim_tempo_cmd("voz.wav", "out.wav", 1.1, trim_silence=False)
    filt = cmd[cmd.index("-af") + 1]
    assert "silenceremove" not in filt
    assert "areverse" not in filt


def test_trim_tempo_cmd_accepts_the_tempo_limits():
    from forja import media

    for tempo in (0.5, 2.0):
        cmd = media.trim_tempo_cmd("voz.wav", "out.wav", tempo)
        assert f"atempo={tempo}" in cmd[cmd.index("-af") + 1]


# ----------------------------------------------------------------- assemble_mix

def test_assemble_mix_writes_stereo_int16_at_original_duration(tmp_path):
    from forja import media

    orig = tmp_path / "orig.wav"
    _write_wav(orig, _const(0.5, 2.0, 8000), 8000)
    out = tmp_path / "mix.wav"
    result = media.assemble_mix(orig, [], [], _cfg(), out, sr=8000)
    assert result == Path(out)
    sr, data = _read_wav(out)
    assert sr == 8000
    assert data.dtype == np.int16
    assert data.shape == (16000, 2)
    assert abs(int(data[8000, 0]) - 16384) <= 4
    assert int(data[8000, 0]) == int(data[8000, 1])


def test_assemble_mix_applies_orig_gain(tmp_path):
    from forja import media

    orig = tmp_path / "orig.wav"
    _write_wav(orig, _const(0.5, 1.0, 8000), 8000)
    out = tmp_path / "mix.wav"
    media.assemble_mix(orig, [], [], _cfg(orig_gain=0.5), out, sr=8000)
    _, data = _read_wav(out)
    assert abs(int(data[4000, 0]) - 8192) <= 4


def test_assemble_mix_applies_duck_envelope_to_original(tmp_path):
    from forja import media, mixlib

    orig = tmp_path / "orig.wav"
    _write_wav(orig, _const(0.5, 2.0, 8000), 8000)
    out = tmp_path / "mix.wav"
    # DESIGN.md chama o terceiro item de "db"; a atenuação esperada é db_to_gain(-20).
    media.assemble_mix(orig, [], [(0.0, 2.0, -20.0)], _cfg(), out, sr=8000)
    _, data = _read_wav(out)
    sample = abs(int(data[8000, 0]))
    expected = 0.5 * mixlib.db_to_gain(-20.0) * 32767
    assert abs(sample - expected) <= 20
    assert sample < 3000


def test_assemble_mix_adds_voice_at_its_start_time(tmp_path):
    from forja import media

    orig = tmp_path / "orig.wav"
    voice = tmp_path / "voice.wav"
    _write_wav(orig, _const(0.0, 2.0, 8000), 8000)
    _write_wav(voice, _const(0.25, 0.5, 8000), 8000)
    out = tmp_path / "mix.wav"
    media.assemble_mix(orig, [{"wav": voice, "start": 1.0}], [], _cfg(), out, sr=8000)
    _, data = _read_wav(out)
    assert abs(int(data[10000, 0]) - 8192) <= 6
    assert int(data[4000, 0]) == 0
    assert int(data[14000, 0]) == 0
    assert int(data[10000, 0]) == int(data[10000, 1])


def test_assemble_mix_scales_peak_to_098_instead_of_clipping(tmp_path):
    from forja import media

    orig = tmp_path / "orig.wav"
    _write_wav(orig, _const(1.0, 1.0, 8000), 8000)
    out = tmp_path / "mix.wav"
    media.assemble_mix(orig, [], [], _cfg(), out, sr=8000)
    _, data = _read_wav(out)
    peak = int(np.max(np.abs(data.astype(np.int32))))
    assert peak <= int(0.98 * 32767) + 2
    assert peak >= int(0.97 * 32767)
    assert peak < 32767


def test_assemble_mix_rejects_original_at_another_sample_rate(tmp_path):
    from forja import media
    from forja.errors import ForjaError

    orig = tmp_path / "orig.wav"
    _write_wav(orig, _const(0.5, 1.0, 16000), 16000)
    with pytest.raises(ForjaError) as excinfo:
        media.assemble_mix(orig, [], [], _cfg(), tmp_path / "mix.wav", sr=8000)
    err = excinfo.value
    assert err.code == "CONFIG_INVALID"
    assert orig.name in f"{err.msg} {err.details}"


def test_assemble_mix_rejects_voice_at_another_sample_rate(tmp_path):
    from forja import media
    from forja.errors import ForjaError

    orig = tmp_path / "orig.wav"
    voice = tmp_path / "voice.wav"
    _write_wav(orig, _const(0.5, 1.0, 8000), 8000)
    _write_wav(voice, _const(0.25, 0.5, 16000), 16000)
    with pytest.raises(ForjaError) as excinfo:
        media.assemble_mix(
            orig, [{"wav": voice, "start": 0.0}], [], _cfg(), tmp_path / "mix.wav", sr=8000
        )
    err = excinfo.value
    assert err.code == "CONFIG_INVALID"
    assert voice.name in f"{err.msg} {err.details}"


def test_assemble_mix_truncates_voice_past_the_end(tmp_path):
    from forja import media

    orig = tmp_path / "orig.wav"
    voice = tmp_path / "voice.wav"
    _write_wav(orig, _const(0.0, 1.0, 8000), 8000)
    _write_wav(voice, _const(0.25, 2.0, 8000), 8000)
    out = tmp_path / "mix.wav"
    media.assemble_mix(orig, [{"wav": voice, "start": 0.8}], [], _cfg(), out, sr=8000)
    _, data = _read_wav(out)
    assert data.shape == (8000, 2)
    assert int(data[7200, 0]) > 0


# -------------------------------------------------------------- measure_loudness

def test_measure_loudness_parses_ffmpeg_json():
    from forja import media, mixlib

    measured = {"input_i": "-18.2", "input_tp": "-2.1", "input_lra": "9.0"}
    stderr = "frame=1\n" + json.dumps(measured) + "\n"
    run, calls = _fake_run(stderr=stderr)
    result = media.measure_loudness("in.wav", _cfg(), run=run)
    assert result == measured
    assert calls[0]["cmd"] == mixlib.loudnorm_measure_cmd("in.wav", -16.0, -1.5, 11.0)


def test_measure_loudness_maps_ffmpeg_failure():
    from forja import media
    from forja.errors import ForjaError

    run, _ = _fake_run(returncode=1, stderr="loudnorm failed")
    with pytest.raises(ForjaError) as excinfo:
        media.measure_loudness("in.wav", _cfg(), run=run)
    assert excinfo.value.code == "PROVIDER_ERROR"


def test_measure_loudness_maps_missing_ffmpeg():
    from forja import media
    from forja.errors import ForjaError

    run, _ = _fake_run(raises=FileNotFoundError("ffmpeg"))
    with pytest.raises(ForjaError) as excinfo:
        media.measure_loudness("in.wav", _cfg(), run=run)
    assert excinfo.value.code == "MISSING_PREREQ"


# ------------------------------------------------------------ normalize_loudness

def test_normalize_loudness_measures_then_applies_two_pass():
    from forja import media, mixlib

    measured = {
        "input_i": "-18.2",
        "input_tp": "-2.1",
        "input_lra": "9.0",
        "input_thresh": "-28.5",
        "target_offset": "0.1",
    }
    stderr = "junk\n" + json.dumps(measured) + "\n"
    run, calls = _fake_run(results=[{"stderr": stderr}, {"returncode": 0}])
    result = media.normalize_loudness("in.wav", "out.wav", _cfg(), run=run)
    assert result == measured
    assert len(calls) == 2
    assert calls[0]["cmd"] == mixlib.loudnorm_measure_cmd("in.wav", -16.0, -1.5, 11.0)
    assert calls[1]["cmd"] == mixlib.loudnorm_apply_cmd(
        "in.wav", "out.wav", -16.0, -1.5, 11.0, measured
    )


def test_normalize_loudness_fails_when_apply_fails():
    from forja import media
    from forja.errors import ForjaError

    measured = {
        "input_i": "-18.2",
        "input_tp": "-2.1",
        "input_lra": "9.0",
        "input_thresh": "-28.5",
        "target_offset": "0.1",
    }
    run, _ = _fake_run(
        results=[{"stderr": json.dumps(measured)}, {"returncode": 1, "stderr": "bad"}]
    )
    with pytest.raises(ForjaError) as excinfo:
        media.normalize_loudness("in.wav", "out.wav", _cfg(), run=run)
    assert excinfo.value.code == "PROVIDER_ERROR"


def test_normalize_loudness_fails_when_measure_fails():
    from forja import media
    from forja.errors import ForjaError

    run, _ = _fake_run(returncode=1, stderr="bad")
    with pytest.raises(ForjaError) as excinfo:
        media.normalize_loudness("in.wav", "out.wav", _cfg(), run=run)
    assert excinfo.value.code == "PROVIDER_ERROR"


# --------------------------------------------------------------- render_remotion

def test_render_remotion_writes_props_next_to_output(tmp_path):
    from forja import media

    out = tmp_path / "out" / "video.mp4"
    out.parent.mkdir()
    props = {"clip": "clip.mp4", "durationS": 2.0, "subs": [{"lines": ["ação"]}]}
    run, _ = _fake_run()
    result = media.render_remotion("src/index.tsx", props, "work", out, run=run)
    props_path = Path(str(out) + ".props.json")
    assert result == Path(out)
    assert props_path.exists()
    assert json.loads(props_path.read_text(encoding="utf-8")) == props


def test_render_remotion_runs_the_render_command(tmp_path):
    from forja import media, render

    out = tmp_path / "video.mp4"
    run, calls = _fake_run()
    media.render_remotion("src/index.tsx", {"clip": "clip.mp4"}, "work", out, run=run)
    props_path = Path(str(out) + ".props.json")
    expected = render.remotion_cmd("src/index.tsx", str(props_path), "work", str(out))
    assert [str(part) for part in calls[0]["cmd"]] == [str(part) for part in expected]


def test_render_remotion_passes_cwd_to_run(tmp_path):
    from forja import media

    out = tmp_path / "video.mp4"
    cwd = tmp_path / "remotion"
    cwd.mkdir()
    run, calls = _fake_run()
    media.render_remotion(
        "src/index.tsx", {"clip": "clip.mp4"}, "work", out, run=run, cwd=cwd
    )
    assert str(calls[0]["kwargs"].get("cwd")) == str(cwd)


def test_render_remotion_propagates_failure(tmp_path):
    from forja import media
    from forja.errors import ForjaError

    run, _ = _fake_run(returncode=1, stderr="render failed")
    with pytest.raises(ForjaError) as excinfo:
        media.render_remotion(
            "src/index.tsx", {"clip": "clip.mp4"}, "work", tmp_path / "video.mp4", run=run
        )
    assert excinfo.value.code == "PROVIDER_ERROR"


# ------------------------------------------------------------------------ mux

def test_mux_runs_the_mux_command_and_returns_path(tmp_path):
    from forja import media, render

    out = tmp_path / "final.mp4"
    run, calls = _fake_run()
    result = media.mux("video.mp4", "mix.wav", out, run=run)
    assert result == Path(out)
    expected = render.mux_cmd("video.mp4", "mix.wav", out)
    assert [str(part) for part in calls[0]["cmd"]] == [str(part) for part in expected]


def test_mux_command_copies_video_and_encodes_aac(tmp_path):
    from forja import media

    run, calls = _fake_run()
    media.mux("video.mp4", "mix.wav", tmp_path / "final.mp4", run=run)
    joined = _joined(calls[0]["cmd"])
    assert "-c:v copy" in joined
    assert "-c:a aac" in joined
    assert "-shortest" in joined
    assert "+faststart" in joined


def test_mux_propagates_ffmpeg_failure(tmp_path):
    from forja import media
    from forja.errors import ForjaError

    run, _ = _fake_run(returncode=1, stderr="mux failed")
    with pytest.raises(ForjaError) as excinfo:
        media.mux("video.mp4", "mix.wav", tmp_path / "final.mp4", run=run)
    assert excinfo.value.code == "PROVIDER_ERROR"


def test_mux_maps_missing_ffmpeg(tmp_path):
    from forja import media
    from forja.errors import ForjaError

    run, _ = _fake_run(raises=FileNotFoundError("ffmpeg"))
    with pytest.raises(ForjaError) as excinfo:
        media.mux("video.mp4", "mix.wav", tmp_path / "final.mp4", run=run)
    assert excinfo.value.code == "MISSING_PREREQ"


# -------------------------------------------------------------- contact_sheet

def test_contact_sheet_rejects_zero_duration(tmp_path):
    from forja import media

    run, _ = _fake_run()
    with pytest.raises(ValueError):
        media.contact_sheet("video.mp4", tmp_path / "sheet.png", 0, run=run)


def test_contact_sheet_rejects_negative_duration(tmp_path):
    from forja import media

    run, _ = _fake_run()
    with pytest.raises(ValueError):
        media.contact_sheet("video.mp4", tmp_path / "sheet.png", -1.0, run=run)


def test_contact_sheet_builds_default_grid_and_returns_path(tmp_path):
    from forja import media

    out = tmp_path / "sheet.png"
    run, calls = _fake_run()
    result = media.contact_sheet("video.mp4", out, 10.0, run=run)
    assert result == Path(out)
    assert len(calls) == 1
    cmd = calls[0]["cmd"]
    joined = _joined(cmd)
    assert abs(_fps_from(cmd) - 1.2) < 1e-9
    assert "scale=320:-1" in joined
    assert "tile=4x3" in joined
    assert "-frames:v" in cmd
    assert cmd[cmd.index("-frames:v") + 1] == "1"


def test_contact_sheet_uses_custom_count_and_columns(tmp_path):
    from forja import media

    run, calls = _fake_run()
    media.contact_sheet("video.mp4", tmp_path / "sheet.png", 10.0, n=7, cols=3, run=run)
    cmd = calls[0]["cmd"]
    joined = _joined(cmd)
    assert abs(_fps_from(cmd) - 0.7) < 1e-9
    assert "tile=3x3" in joined


def test_contact_sheet_propagates_ffmpeg_failure(tmp_path):
    from forja import media
    from forja.errors import ForjaError

    run, _ = _fake_run(returncode=1, stderr="sheet failed")
    with pytest.raises(ForjaError) as excinfo:
        media.contact_sheet("video.mp4", tmp_path / "sheet.png", 10.0, run=run)
    assert excinfo.value.code == "PROVIDER_ERROR"


def test_render_remotion_passes_the_composition_to_the_command(tmp_path):
    import subprocess

    from forja import media

    seen = []

    def fake_run(cmd, **kwargs):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    media.render_remotion("src/index.jsx", {"a": 1}, tmp_path, tmp_path / "o.mp4", run=fake_run, composition="Storyboard")
    assert "Storyboard" in seen[0] and "Legendas" not in seen[0]


def test_run_checked_does_not_pass_secrets_to_subprocess(monkeypatch):
    from forja import media

    monkeypatch.setenv("GEMINI_API_KEY", "segredo-que-nao-pode-vazar")
    run, calls = _fake_run()
    media.run_checked(["ffmpeg", "-version"], run=run)
    passed = calls[0]["kwargs"].get("env") or {}
    assert "GEMINI_API_KEY" not in passed
    assert passed.get("PATH")
