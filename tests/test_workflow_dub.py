"""Integracao do workflow ``dub``: ffmpeg real, resto simulado.

Os imports de ``forja`` ficam dentro das fixtures/testes de proposito: a
coleta precisa funcionar mesmo antes de os corpos dos passos existirem.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

_HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH"
)

STEP_NAMES = [
    "clip",
    "orig",
    "transcribe",
    "check",
    "voices",
    "schedule",
    "mix",
    "render",
    "qa",
]

_CUES = [
    {
        "id": "A",
        "role": "narrator",
        "t0": 0.5,
        "t1": 3.5,
        "text": "Aqui começa tudo.",
    },
    {
        "id": "B",
        "role": "speech",
        "t0": 4.0,
        "t1": 7.0,
        "text": "Esta é a história.",
    },
]


@pytest.fixture(scope="module", autouse=True)
def _ffmpeg_ok():
    """Guarda redundante: o skipif do modulo cobre a coleta inteira."""
    if not _HAS_FFMPEG:
        pytest.skip("ffmpeg/ffprobe nao encontrados no PATH")


def _write_cues(root: Path, cues) -> None:
    (root / "cues.json").write_text(
        json.dumps(cues, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _write_lower_thirds(root: Path, windows) -> None:
    (root / "lower_thirds.json").write_text(
        json.dumps(windows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _configure(root: Path) -> None:
    """Ajusta o config do projeto para o teste: mock + video relativo."""
    import yaml

    from forja import config

    cfg = config.load_config(root / "config.yaml")
    cfg["voices"]["provider"] = "mock"
    cfg["input"]["video"] = "input/source.mp4"
    cfg["input"]["start"] = 0.0
    cfg["input"]["duration"] = None
    (root / "config.yaml").write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def _new_project(root: Path, source_video: Path) -> Path:
    from forja import project

    root = Path(root)
    project.scaffold(root, "demo", source=None, workflow="dub")
    shutil.copyfile(source_video, root / "input" / "source.mp4")
    _configure(root)
    _write_cues(root, _CUES)
    _write_lower_thirds(root, [])
    return root


def _make_ctx(root: Path):
    from forja import steps
    from forja.project import Project

    project = Project(root)
    cfg = project.load_config()
    return steps.Ctx(
        root=Path(root),
        cfg=cfg,
        work=project.work,
        out=project.out,
        env={},
        log=lambda _message: None,
        dry_run=False,
    )


def _dub_steps():
    from forja import workflows
    from forja.workflows import dub as _dub  # noqa: F401  (registra o workflow)

    return workflows.get_workflow("dub").steps_factory()


@pytest.fixture(scope="module")
def source_video(tmp_path_factory):
    """Video sintetico de 8 s com video e audio, gerado por ffmpeg real."""
    path = tmp_path_factory.mktemp("media") / "source.mp4"
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x180:rate=30:duration=8",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=220:duration=8",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail("ffmpeg falhou ao gerar o video sintetico:\n" + result.stderr[-1500:])
    return path


@pytest.fixture(scope="module")
def simulations():
    """Troca as bordas externas caras (Whisper/Remotion) por versoes locais."""
    from forja import media, transcribe

    monkey = pytest.MonkeyPatch()

    def fake_run_transcribe(wav, cfg, model_dir):
        return {
            "language": "en",
            "duration": 8.0,
            "segments": [
                {
                    "start": 0.0,
                    "end": 8.0,
                    "text": "hello world",
                    "words": [
                        {"word": "hello", "start": 0.0, "end": 4.0},
                        {"word": "world", "start": 4.0, "end": 8.0},
                    ],
                }
            ],
        }

    def fake_render_remotion(entry, props, public_dir, out, run=None, cwd=None):
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        source = Path(public_dir) / "clip.mp4"
        shutil.copyfile(source, out)
        return out

    monkey.setattr(transcribe, "run_transcribe", fake_run_transcribe)
    monkey.setattr(media, "render_remotion", fake_render_remotion)
    try:
        yield monkey
    finally:
        monkey.undo()


@pytest.fixture(scope="module")
def stepwise(simulations, source_video, tmp_path_factory):
    """Projeto em que cada passo roda sozinho, na ordem do contrato."""
    from forja import steps

    root = _new_project(tmp_path_factory.mktemp("stepwise") / "p", source_video)
    ctx = _make_ctx(root)
    steps_list = _dub_steps()
    results = {}
    for step in steps_list:
        results[step.name] = steps.run_steps(ctx, steps_list, only=[step.name])
    return SimpleNamespace(root=root, ctx=ctx, steps=steps_list, results=results)


@pytest.fixture(scope="module")
def built(simulations, source_video, tmp_path_factory):
    """Projeto com o pipeline completo executado de uma vez."""
    from forja import steps

    root = _new_project(tmp_path_factory.mktemp("built") / "p", source_video)
    ctx = _make_ctx(root)
    steps_list = _dub_steps()
    results = steps.run_steps(ctx, steps_list)
    return SimpleNamespace(root=root, ctx=ctx, steps=steps_list, results=results)


def _refresh_manifest(ctx, steps_list) -> None:
    """Marca o clone como fresco, recalculando hashes para os caminhos novos."""
    from forja import cache

    manifest = cache.Manifest(ctx.work / "manifest.json")
    for step in steps_list:
        paths, extra = step.inputs(ctx)
        manifest.put(step.name, cache.hash_inputs(paths, extra), step.outputs(ctx))
    manifest.save()


@pytest.fixture
def clone(built, tmp_path):
    """Copia barata do projeto construido, com manifesto coerente."""
    root = tmp_path / "p"
    shutil.copytree(built.root, root)
    ctx = _make_ctx(root)
    steps_list = _dub_steps()
    _refresh_manifest(ctx, steps_list)
    return SimpleNamespace(root=root, ctx=ctx, steps=steps_list)


# --------------------------------------------------------------------- ordem


def test_steps_factory_matches_contract_order_and_needs():
    steps_list = _dub_steps()
    assert [step.name for step in steps_list] == STEP_NAMES
    needs = {step.name: step.needs for step in steps_list}
    assert needs["clip"] == []
    assert needs["orig"] == ["clip"]
    assert needs["transcribe"] == ["orig"]
    assert needs["check"] == []
    assert needs["voices"] == ["check"]
    assert needs["schedule"] == ["voices"]
    assert set(needs["mix"]) == {"schedule", "orig"}
    assert needs["render"] == ["mix"]
    assert needs["qa"] == ["render"]


def test_stepwise_each_step_runs_alone_and_ok(stepwise):
    assert list(stepwise.results) == STEP_NAMES
    for name, result in stepwise.results.items():
        assert len(result) == 1, (name, result)
        assert result[0]["step"] == name
        assert result[0]["status"] == "ok", (name, result[0])


# ---------------------------------------------------------------- cada passo


def test_step_clip_writes_clip_and_metadata(stepwise):
    root = stepwise.root
    clip = root / "work" / "clip.mp4"
    assert clip.is_file() and clip.stat().st_size > 0
    meta = json.loads((root / "work" / "clip.json").read_text(encoding="utf-8"))
    assert abs(float(meta["duration"]) - 8.0) <= 0.25
    assert int(meta["width"]) == 320
    assert int(meta["height"]) == 180
    assert abs(float(meta["fps"]) - 30.0) <= 0.5
    assert meta["has_audio"] is True


def test_step_orig_writes_48k_stereo_wav(stepwise):
    path = stepwise.root / "work" / "orig.wav"
    assert path.is_file()
    with wave.open(str(path), "rb") as wav:
        assert wav.getnchannels() == 2
        assert wav.getframerate() == 48000
        duration = wav.getnframes() / float(wav.getframerate())
    assert abs(duration - 8.0) <= 0.25


def test_step_transcribe_writes_transcript_json(stepwise):
    data = json.loads(
        (stepwise.root / "work" / "transcript.json").read_text(encoding="utf-8")
    )
    assert data["language"] == "en"
    assert abs(float(data["duration"]) - 8.0) <= 0.25
    assert isinstance(data["segments"], list) and data["segments"]
    segment = data["segments"][0]
    assert {"start", "end", "text", "words"} <= set(segment)


def test_step_check_writes_ok_summary(stepwise):
    summary = json.loads(
        (stepwise.root / "work" / "check.json").read_text(encoding="utf-8")
    )
    assert summary["ok"] is True
    assert summary["errors"] == 0
    assert isinstance(summary["issues"], list)


def test_step_voices_writes_manifest_and_wavs(stepwise):
    root = stepwise.root
    manifest = json.loads(
        (root / "work" / "voices" / "manifest.json").read_text(encoding="utf-8")
    )
    assert {"A", "B"} <= set(manifest)
    for cue_id in ("A", "B"):
        entry = manifest[cue_id]
        assert float(entry["duration"]) > 0.0
        wav_path = root / Path(entry["wav"])
        assert wav_path.is_file(), wav_path
        with wave.open(str(wav_path), "rb") as wav:
            assert wav.getnframes() > 0


def test_step_schedule_writes_plan_subs_and_srt(stepwise):
    root = stepwise.root
    plan = json.loads((root / "work" / "plan.json").read_text(encoding="utf-8"))
    assert abs(float(plan["total"]) - 8.0) <= 0.25
    assert [cue["id"] for cue in plan["cues"]] == ["A", "B"]
    for cue in plan["cues"]:
        assert {
            "id",
            "start",
            "end",
            "tempo",
            "trim_start",
            "trim_end",
            "lag",
            "warnings",
        } <= set(cue)

    subs = json.loads((root / "work" / "subs.json").read_text(encoding="utf-8"))
    assert len(subs) == 2
    for event in subs:
        assert {"start", "end", "lines", "narrador", "raised"} <= set(event)

    srt = (root / "out" / "legendas.srt").read_text(encoding="utf-8")
    blocks = [block for block in re.split(r"\n\s*\n", srt.strip()) if block.strip()]
    assert len(blocks) == 2
    assert all("-->" in block for block in blocks)


def test_step_mix_writes_stereo_wav_and_loudness(stepwise):
    from scipy.io import wavfile

    root = stepwise.root
    sample_rate, samples = wavfile.read(str(root / "work" / "mix.wav"))
    assert int(sample_rate) == 48000
    assert samples.ndim == 2 and samples.shape[1] == 2
    assert abs(samples.shape[0] / float(sample_rate) - 8.0) <= 0.25

    loudness = json.loads(
        (root / "work" / "loudness.json").read_text(encoding="utf-8")
    )
    assert "I" in loudness and "TP" in loudness
    assert float(loudness["I"]) < 0.0
    assert float(loudness["TP"]) <= 0.0
    for cue_id in ("A", "B"):
        assert (root / "work" / "voices" / (cue_id + ".fit.wav")).is_file()


def test_step_render_writes_video_with_video_and_audio(stepwise):
    from forja import probe

    video = stepwise.root / "out" / "video.mp4"
    assert video.is_file() and video.stat().st_size > 0
    info = probe.probe_video(video)
    assert info["has_audio"] is True
    assert abs(float(info["duration"]) - 8.0) <= 0.35


def test_step_qa_writes_ok_report(stepwise):
    report = json.loads(
        (stepwise.root / "out" / "qa.json").read_text(encoding="utf-8")
    )
    assert report["ok"] is True
    assert report["errors"] == 0
    assert isinstance(report["issues"], list)


# --------------------------------------------------------------- pipeline


def test_full_pipeline_runs_all_steps_ok(built):
    assert [result["step"] for result in built.results] == STEP_NAMES
    assert all(result["status"] == "ok" for result in built.results)
    for result in built.results:
        for output in result["outputs"]:
            assert Path(output).exists(), (result["step"], output)
    assert json.loads(
        (built.root / "out" / "qa.json").read_text(encoding="utf-8")
    )["ok"] is True


def test_second_run_is_all_skipped_by_cache(built):
    from forja import steps

    second = steps.run_steps(built.ctx, _dub_steps())
    assert [result["step"] for result in second] == STEP_NAMES
    assert all(result["status"] == "skipped" for result in second)


def test_editing_cue_text_reruns_dependent_steps_only(clone):
    from forja import steps

    cues = json.loads((clone.root / "cues.json").read_text(encoding="utf-8"))
    for cue in cues:
        if cue["id"] == "A":
            cue["text"] = "Aqui começa a jornada."
    _write_cues(clone.root, cues)

    results = steps.run_steps(clone.ctx, clone.steps)
    status = {result["step"]: result["status"] for result in results}
    for name in ("check", "voices", "schedule", "mix", "render", "qa"):
        assert status[name] == "ok", (name, status)
    for name in ("clip", "orig"):
        assert status[name] == "skipped", (name, status)

    subs = json.loads((clone.root / "work" / "subs.json").read_text(encoding="utf-8"))
    text = " ".join(" ".join(event["lines"]) for event in subs)
    assert "jornada" in text
    assert json.loads(
        (clone.root / "out" / "qa.json").read_text(encoding="utf-8")
    )["ok"] is True


# ------------------------------------------------------------------ gates


def test_check_rejects_invalid_cue_time_order(clone):
    from forja import errors, steps

    cues = json.loads((clone.root / "cues.json").read_text(encoding="utf-8"))
    for cue in cues:
        if cue["id"] == "B":
            cue["t1"] = 3.9
    _write_cues(clone.root, cues)

    with pytest.raises(errors.ForjaError) as excinfo:
        steps.run_steps(clone.ctx, clone.steps, only=["check"])
    error = excinfo.value
    assert error.code == "GATE_FAILED"
    assert error.details and isinstance(error.details.get("issues"), list)
    assert any(
        issue.get("code") == "T_ORDER" for issue in error.details["issues"]
    )


def test_voices_gemini_without_key_fails_without_leaking_secret(clone, monkeypatch):
    import yaml

    from forja import errors

    secret = "sk-test-NAO-VAZAR"
    monkeypatch.setenv("OUTRO_SEGREDO", secret)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    config_path = clone.root / "config.yaml"
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["voices"]["provider"] = "gemini"
    cfg["voices"]["api_key_env"] = "GEMINI_API_KEY"
    config_path.write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    ctx = _make_ctx(clone.root)
    ctx.env = {}

    voices = next(step for step in clone.steps if step.name == "voices")
    with pytest.raises((errors.ForjaError, RuntimeError)) as excinfo:
        voices.run(ctx)

    message = str(excinfo.value)
    assert "GEMINI_API_KEY" in message
    assert secret not in message
    if isinstance(excinfo.value, errors.ForjaError):
        assert excinfo.value.code == "MISSING_KEY"


def test_qa_fails_on_out_of_range_loudness(clone):
    from forja import errors, steps

    (clone.root / "work" / "loudness.json").write_text(
        json.dumps({"I": -40.0, "TP": -2.0}, indent=2) + "\n", encoding="utf-8"
    )

    with pytest.raises(errors.ForjaError) as excinfo:
        steps.run_steps(clone.ctx, clone.steps, only=["qa"])
    error = excinfo.value
    assert error.code == "GATE_FAILED"
    issues = (error.details or {}).get("issues") or []
    assert any(
        issue.get("code") == "LUFS" and issue.get("level") == "error"
        for issue in issues
    )


def test_missing_lower_thirds_is_treated_as_empty(clone):
    from forja import steps

    root = clone.root
    (root / "lower_thirds.json").unlink()
    # Remove saidas para garantir que os passos rodem de novo mesmo se a
    # implementacao nao listar lower_thirds.json entre as entradas.
    (root / "work" / "plan.json").unlink()
    (root / "out" / "legendas.srt").unlink()
    schedule = steps.run_steps(clone.ctx, clone.steps, only=["schedule"])
    assert [result["status"] for result in schedule] == ["ok"]

    subs = json.loads((root / "work" / "subs.json").read_text(encoding="utf-8"))
    assert len(subs) == 2
    assert all(event["raised"] is False for event in subs)

    (root / "out" / "video.mp4").unlink()
    render = steps.run_steps(clone.ctx, clone.steps, only=["render"])
    assert [result["status"] for result in render] == ["ok"]
    assert (root / "out" / "video.mp4").is_file()

    (root / "out" / "qa.json").unlink()
    qa = steps.run_steps(clone.ctx, clone.steps, only=["qa"])
    assert [result["status"] for result in qa] == ["ok"]
    report = json.loads((root / "out" / "qa.json").read_text(encoding="utf-8"))
    assert report["ok"] is True


def test_voices_rejects_unsafe_cue_id_without_writing_outside(clone):
    from forja import errors

    cues = json.loads((clone.root / "cues.json").read_text(encoding="utf-8"))
    cues[0]["id"] = "../../../PWNED"
    _write_cues(clone.root, cues)

    voices = next(step for step in clone.steps if step.name == "voices")
    with pytest.raises(errors.ForjaError) as excinfo:
        voices.run(clone.ctx)
    assert excinfo.value.code == "CONFIG_INVALID"
    assert not (clone.root.parent / "PWNED.wav").exists()


def test_corrupt_generated_json_fails_with_a_clear_error(clone):
    from forja import errors, steps

    (clone.root / "work" / "clip.json").write_text("{nao e json", encoding="utf-8")
    with pytest.raises(errors.ForjaError) as excinfo:
        steps.run_steps(clone.ctx, clone.steps, only=["schedule"])
    assert excinfo.value.code == "MISSING_INPUT"
    assert "ilegivel" in str(excinfo.value)


def test_voices_files_provider_reads_project_wavs(clone):
    import yaml

    from forja import tts

    cfg_path = clone.root / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    cfg["voices"]["provider"] = "files"
    cfg["voices"]["input_dir"] = "voices"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (clone.root / "voices").mkdir(exist_ok=True)
    for cue_id in ("A", "B"):
        (clone.root / "voices" / (cue_id + ".wav")).write_bytes(tts.mock_wav("teste"))

    ctx = _make_ctx(clone.root)
    voices = next(step for step in clone.steps if step.name == "voices")
    voices.run(ctx)
    manifest = json.loads((clone.root / "work" / "voices" / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == {"A", "B"}
