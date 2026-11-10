"""Contratos de forja.probe descritos no DESIGN.md."""
import json
from types import SimpleNamespace

import pytest


def _payload(duration="10.5", width=1280, height=720, fps="30/1", audio=True):
    streams = [
        {
            "codec_type": "video",
            "width": width,
            "height": height,
            "avg_frame_rate": fps,
            "r_frame_rate": fps,
            "duration": duration,
        }
    ]
    if audio:
        streams.append({"codec_type": "audio", "codec_name": "aac"})
    return {"streams": streams, "format": {"duration": duration}}


def _fake_run(payload, calls=None):
    calls = [] if calls is None else calls

    def run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(
            stdout=json.dumps(payload), stderr="", returncode=0
        )

    return run, calls


def test_probe_video_returns_documented_keys():
    from forja import probe

    run, _ = _fake_run(_payload())
    info = probe.probe_video("input/clip.mp4", run=run)
    assert set(info) == {"duration", "width", "height", "fps", "has_audio"}


def test_probe_video_parses_dimensions_and_duration():
    from forja import probe

    run, _ = _fake_run(_payload())
    info = probe.probe_video("input/clip.mp4", run=run)
    assert (info["duration"], info["width"], info["height"]) == (10.5, 1280, 720)


def test_probe_video_parses_fps():
    from forja import probe

    run, _ = _fake_run(_payload(fps="30/1"))
    info = probe.probe_video("input/clip.mp4", run=run)
    assert info["fps"] == pytest.approx(30.0)


def test_probe_video_reports_audio_present():
    from forja import probe

    run, _ = _fake_run(_payload(audio=True))
    info = probe.probe_video("input/clip.mp4", run=run)
    assert info["has_audio"] is True


def test_probe_video_reports_audio_absent():
    from forja import probe

    run, _ = _fake_run(_payload(audio=False))
    info = probe.probe_video("input/clip.mp4", run=run)
    assert info["has_audio"] is False


def test_probe_video_raises_without_a_video_stream():
    from forja import probe

    payload = {
        "streams": [{"codec_type": "audio", "codec_name": "aac"}],
        "format": {"duration": "10.5"},
    }
    run, _ = _fake_run(payload)
    with pytest.raises(RuntimeError):
        probe.probe_video("input/clip.mp4", run=run)


def test_probe_video_raises_without_any_stream():
    from forja import probe

    run, _ = _fake_run({"streams": [], "format": {"duration": "10.5"}})
    with pytest.raises(RuntimeError):
        probe.probe_video("input/clip.mp4", run=run)


def _command_text(command):
    if isinstance(command, str):
        return command
    return " ".join(str(part) for part in command)


def test_probe_video_uses_ffprobe_with_json_output():
    from forja import probe

    run, calls = _fake_run(_payload())
    probe.probe_video("input/clip.mp4", run=run)
    command = _command_text(calls[0])
    assert "ffprobe" in command and "-print_format" in command and "json" in command


def test_probe_video_passes_the_media_path_to_ffprobe():
    from forja import probe

    run, calls = _fake_run(_payload())
    probe.probe_video("input/clip.mp4", run=run)
    assert "input/clip.mp4" in _command_text(calls[0])


def test_probe_video_returns_numeric_duration_and_fps():
    from forja import probe

    run, _ = _fake_run(_payload())
    info = probe.probe_video("input/clip.mp4", run=run)
    assert isinstance(info["duration"], float)
    assert isinstance(info["fps"], (int, float))


def test_probe_does_not_pass_secrets_to_subprocess(monkeypatch):
    import json as jsonlib
    from types import SimpleNamespace

    from forja import probe

    monkeypatch.setenv("GEMINI_API_KEY", "segredo-que-nao-pode-vazar")
    seen = {}

    def run(cmd, **kwargs):
        seen.update(kwargs)
        return SimpleNamespace(stdout=jsonlib.dumps(_payload()), stderr="", returncode=0)

    probe.probe_video("input/clip.mp4", run=run)
    assert "GEMINI_API_KEY" not in (seen.get("env") or {})
