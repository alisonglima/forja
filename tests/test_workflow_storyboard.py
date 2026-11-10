"""Integracao do workflow ``storyboard``: ffmpeg real, TTS mock e Remotion simulado.

Os imports de ``forja`` ficam dentro das fixtures/testes de proposito: a coleta
precisa funcionar mesmo antes de os corpos dos passos existirem.
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

STEP_NAMES = ["validate", "voices", "timeline", "mix", "render", "qa"]
PAD_BEFORE = 0.3
PAD_AFTER = 0.4
S2_FIXED_S = 3.0
NARRATION_S1 = "O passeio comeca cedo pela manha."
NARRATION_S1_EDIT = "O passeio segue por outro caminho."


def _ffmpeg(cmd) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail("ffmpeg falhou:\n" + (result.stderr or "")[-1500:])


def _make_assets(root: Path) -> dict:
    """Gera os tres assets sinteticos usados pelo storyboard."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    clip = root / "clip.mp4"
    _ffmpeg(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x180:rate=30:duration=6",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-t",
            "6",
            str(clip),
        ]
    )
    card = root / "card.png"
    _ffmpeg(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x1E88E5:s=320x180:d=1",
            "-frames:v",
            "1",
            str(card),
        ]
    )
    trilha = root / "trilha.wav"
    _ffmpeg(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:duration=10:sample_rate=48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(trilha),
        ]
    )
    return {"clip.mp4": clip, "card.png": card, "trilha.wav": trilha}


def _storyboard() -> dict:
    return {
        "version": 1,
        "canvas": {"w": 320, "h": 180, "fps": 30},
        "scenes": [
            {
                "id": "S1",
                "duration": {
                    "from": "narration",
                    "pad_before": PAD_BEFORE,
                    "pad_after": PAD_AFTER,
                },
                "layers": [
                    {
                        "type": "clip",
                        "file": "assets/clip.mp4",
                        "in_s": 0,
                        "fit": "cover",
                    },
                    {"type": "narration", "text": NARRATION_S1, "lang": "pt-BR"},
                    {"type": "captions", "from": "narration"},
                    {
                        "type": "music",
                        "track": "assets/trilha.wav",
                        "gain_db": -12,
                        "license": {"kind": "cc0"},
                    },
                ],
            },
            {
                "id": "S2",
                "duration": {"fixed_s": S2_FIXED_S},
                "layers": [
                    {
                        "type": "clip",
                        "file": "assets/clip.mp4",
                        "in_s": 0,
                        "fit": "cover",
                    },
                    {"type": "card", "asset": "assets/card.png"},
                ],
            },
        ],
    }


def _write_storyboard(root: Path, storyboard: dict) -> None:
    import yaml

    (Path(root) / "storyboard.yaml").write_text(
        yaml.safe_dump(storyboard, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _configure(root: Path) -> None:
    """Ajusta o config do projeto para o teste: TTS mock."""
    import yaml

    from forja import config

    cfg = config.load_config(Path(root) / "config.yaml")
    cfg["voices"]["provider"] = "mock"
    (Path(root) / "config.yaml").write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def _new_project(root: Path, assets: dict) -> Path:
    from forja import project

    root = Path(root)
    project.scaffold(root, "demo", workflow="storyboard")
    assets_dir = root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for name, source in assets.items():
        shutil.copyfile(source, assets_dir / name)
    _configure(root)
    _write_storyboard(root, _storyboard())
    return root


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


def _storyboard_steps():
    from forja import workflows
    from forja.workflows import storyboard as _storyboard  # noqa: F401  (registra)

    return workflows.get_workflow("storyboard").steps_factory()


def _read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _refresh_manifest(ctx, steps_list) -> None:
    """Marca o clone como fresco, recalculando hashes para os caminhos novos."""
    from forja import cache

    manifest = cache.Manifest(ctx.work / "manifest.json")
    for step in steps_list:
        paths, extra = step.inputs(ctx)
        manifest.put(step.name, cache.hash_inputs(paths, extra), step.outputs(ctx))
    manifest.save()


@pytest.fixture(scope="module")
def assets(tmp_path_factory):
    return _make_assets(tmp_path_factory.mktemp("assets"))


@pytest.fixture(scope="module")
def simulations(tmp_path_factory):
    """Troca o Remotion real por um mp4 sintetico com a duracao da timeline."""
    from forja import media

    monkey = pytest.MonkeyPatch()
    cache = tmp_path_factory.mktemp("render")

    def fake_render_remotion(
        entry, props, public_dir=None, out=None, run=None, cwd=None, composition=None
    ):
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        total = float(props.get("durationS") or 0.0)
        if total <= 0:
            total = float((props.get("timeline") or {}).get("total_s") or 0.0)
        if total <= 0:
            total = 1.0
        source = cache / ("testsrc-%.3f.mp4" % total)
        if not source.is_file():
            _ffmpeg(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=size=320x180:rate=30:duration=%s" % total,
                    "-an",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-t",
                    str(total),
                    str(source),
                ]
            )
        shutil.copyfile(source, out)
        return out

    monkey.setattr(media, "render_remotion", fake_render_remotion)
    try:
        yield monkey
    finally:
        monkey.undo()


@pytest.fixture(scope="module")
def stepwise(simulations, assets, tmp_path_factory):
    """Projeto em que cada passo roda sozinho, na ordem do contrato."""
    from forja import steps

    root = _new_project(tmp_path_factory.mktemp("stepwise") / "p", assets)
    ctx = _make_ctx(root)
    steps_list = _storyboard_steps()
    results = {}
    for step in steps_list:
        results[step.name] = steps.run_steps(ctx, steps_list, only=[step.name])
    return SimpleNamespace(root=root, ctx=ctx, steps=steps_list, results=results)


@pytest.fixture(scope="module")
def built(simulations, assets, tmp_path_factory):
    """Projeto com o pipeline completo executado de uma vez."""
    from forja import steps

    root = _new_project(tmp_path_factory.mktemp("built") / "p", assets)
    ctx = _make_ctx(root)
    steps_list = _storyboard_steps()
    results = steps.run_steps(ctx, steps_list)
    return SimpleNamespace(root=root, ctx=ctx, steps=steps_list, results=results)


@pytest.fixture
def clone(built, tmp_path):
    """Copia barata do projeto construido, com manifesto coerente."""
    root = tmp_path / "p"
    shutil.copytree(built.root, root)
    ctx = _make_ctx(root)
    steps_list = _storyboard_steps()
    _refresh_manifest(ctx, steps_list)
    return SimpleNamespace(root=root, ctx=ctx, steps=steps_list)


# --------------------------------------------------------------------- ordem


def test_steps_factory_matches_contract_order_and_needs():
    steps_list = _storyboard_steps()
    assert [step.name for step in steps_list] == STEP_NAMES
    needs = {step.name: step.needs for step in steps_list}
    assert needs["validate"] == []
    assert needs["voices"] == ["validate"]
    assert needs["timeline"] == ["voices"]
    assert needs["mix"] == ["timeline"]
    assert needs["render"] == ["mix"]
    assert needs["qa"] == ["render"]


def test_stepwise_each_step_runs_alone_and_ok(stepwise):
    assert list(stepwise.results) == STEP_NAMES
    for name, result in stepwise.results.items():
        assert len(result) == 1, (name, result)
        assert result[0]["step"] == name
        assert result[0]["status"] == "ok", (name, result[0])


# ---------------------------------------------------------------- cada passo


def test_step_validate_writes_ok_summary(stepwise):
    summary = _read_json(stepwise.root / "work" / "validate.json")
    assert summary["ok"] is True
    assert summary["errors"] == 0
    assert isinstance(summary["issues"], list)


def test_step_voices_writes_manifest_only_for_narrated_scenes(stepwise):
    root = stepwise.root
    manifest = _read_json(root / "work" / "voices" / "manifest.json")
    assert "S1" in manifest
    assert "S2" not in manifest
    entry = manifest["S1"]
    assert float(entry["duration"]) > 0.0
    wav_path = root / Path(entry["wav"])
    assert wav_path.is_file(), wav_path
    with wave.open(str(wav_path), "rb") as wav:
        assert wav.getnframes() > 0


def test_step_timeline_writes_timeline_subs_and_one_srt_block(stepwise):
    root = stepwise.root
    manifest = _read_json(root / "work" / "voices" / "manifest.json")
    timeline = _read_json(root / "work" / "timeline.json")
    expected_s1 = PAD_BEFORE + float(manifest["S1"]["duration"]) + PAD_AFTER

    assert len(timeline["scenes"]) == 2
    assert timeline["fps"] == 30
    s1 = next(scene for scene in timeline["scenes"] if scene["id"] == "S1")
    assert s1["end"] - s1["start"] == pytest.approx(expected_s1, abs=0.05)
    assert timeline["total_s"] == pytest.approx(expected_s1 + S2_FIXED_S, abs=0.05)

    subs = _read_json(root / "work" / "subs.json")
    assert isinstance(subs, list) and len(subs) == 1
    assert {"start", "end", "lines", "narrador", "raised"} <= set(subs[0])

    srt = (root / "out" / "legendas.srt").read_text(encoding="utf-8")
    blocks = [block for block in re.split(r"\n\s*\n", srt.strip()) if block.strip()]
    assert len(blocks) == 1
    assert "-->" in blocks[0]


def test_step_mix_writes_stereo_wav_and_loudness(stepwise):
    from scipy.io import wavfile

    root = stepwise.root
    sample_rate, samples = wavfile.read(str(root / "work" / "mix.wav"))
    timeline = _read_json(root / "work" / "timeline.json")
    assert int(sample_rate) == 48000
    assert samples.ndim == 2 and samples.shape[1] == 2
    duration = samples.shape[0] / float(sample_rate)
    assert duration == pytest.approx(float(timeline["total_s"]), abs=0.25)

    loudness = _read_json(root / "work" / "loudness.json")
    assert "I" in loudness and "TP" in loudness
    assert float(loudness["I"]) < 0.0
    assert float(loudness["TP"]) <= 0.0
    assert (root / "work" / "bed.wav").is_file()
    assert (root / "work" / "voices" / "S1.fit.wav").is_file()


def test_step_render_writes_video_with_audio(stepwise):
    from forja import probe

    root = stepwise.root
    timeline = _read_json(root / "work" / "timeline.json")
    video = root / "out" / "video.mp4"
    assert video.is_file() and video.stat().st_size > 0
    info = probe.probe_video(video)
    assert info["has_audio"] is True
    assert info["duration"] == pytest.approx(float(timeline["total_s"]), abs=0.5)


def test_step_qa_writes_ok_report(stepwise):
    report = _read_json(stepwise.root / "out" / "qa.json")
    assert report["ok"] is True
    assert report["errors"] == 0
    assert isinstance(report["issues"], list)


def test_scene_duration_equals_pads_plus_manifest_narration(stepwise):
    root = stepwise.root
    manifest = _read_json(root / "work" / "voices" / "manifest.json")
    timeline = _read_json(root / "work" / "timeline.json")
    s1 = next(scene for scene in timeline["scenes"] if scene["id"] == "S1")
    expected = PAD_BEFORE + float(manifest["S1"]["duration"]) + PAD_AFTER
    assert s1["end"] - s1["start"] == pytest.approx(expected, abs=0.05)


# ------------------------------------------------------------------ pipeline


def test_full_pipeline_runs_all_steps_ok(built):
    assert [result["step"] for result in built.results] == STEP_NAMES
    assert all(result["status"] == "ok" for result in built.results)
    for result in built.results:
        for output in result["outputs"]:
            assert Path(output).exists(), (result["step"], output)
    assert _read_json(built.root / "out" / "qa.json")["ok"] is True


def test_second_run_is_all_skipped_by_cache(built):
    from forja import steps

    second = steps.run_steps(built.ctx, _storyboard_steps())
    assert [result["step"] for result in second] == STEP_NAMES
    assert all(result["status"] == "skipped" for result in second)


def test_editing_narration_reruns_downstream_and_validate(clone):
    import yaml

    from forja import steps

    storyboard = yaml.safe_load(
        (clone.root / "storyboard.yaml").read_text(encoding="utf-8")
    )
    for scene in storyboard["scenes"]:
        if scene["id"] == "S1":
            for layer in scene["layers"]:
                if layer["type"] == "narration":
                    layer["text"] = NARRATION_S1_EDIT
    _write_storyboard(clone.root, storyboard)

    results = steps.run_steps(clone.ctx, clone.steps)
    status = {result["step"]: result["status"] for result in results}
    for name in ("validate", "voices", "timeline", "mix", "render", "qa"):
        assert status[name] == "ok", (name, status)

    subs = _read_json(clone.root / "work" / "subs.json")
    text = " ".join(" ".join(event["lines"]) for event in subs)
    assert "caminho" in text
    assert _read_json(clone.root / "out" / "qa.json")["ok"] is True


# --------------------------------------------------------------------- gates


def _gate_error(root: Path, code: str):
    from forja import errors, steps

    with pytest.raises(errors.ForjaError) as excinfo:
        steps.run_steps(_make_ctx(root), _storyboard_steps(), only=["validate"])
    error = excinfo.value
    assert error.code == "GATE_FAILED"
    issues = (error.details or {}).get("issues") or []
    assert any(issue.get("code") == code for issue in issues), issues
    return error


def test_validate_rejects_music_without_license(assets, tmp_path):
    root = _new_project(tmp_path / "p", assets)
    storyboard = _storyboard()
    for layer in storyboard["scenes"][0]["layers"]:
        if layer["type"] == "music":
            layer.pop("license")
    _write_storyboard(root, storyboard)
    _gate_error(root, "MUSIC_NO_LICENSE")


def test_validate_rejects_missing_asset(assets, tmp_path):
    root = _new_project(tmp_path / "p", assets)
    storyboard = _storyboard()
    for layer in storyboard["scenes"][0]["layers"]:
        if layer["type"] == "clip":
            layer["file"] = "assets/nao-existe.mp4"
    _write_storyboard(root, storyboard)
    _gate_error(root, "ASSET_MISSING")


def test_mix_includes_sfx_and_kept_clip_audio(simulations, assets, tmp_path):
    from forja import steps

    root = _new_project(tmp_path / "p", assets)
    storyboard = _storyboard()
    s1 = storyboard["scenes"][0]
    for layer in s1["layers"]:
        if layer["type"] == "clip":
            layer["audio"] = {"mode": "keep"}
    s1["layers"].append(
        {"type": "sfx", "file": "assets/trilha.wav", "license": {"kind": "cc0"}}
    )
    _write_storyboard(root, storyboard)

    ctx = _make_ctx(root)
    steps_list = _storyboard_steps()
    results = steps.run_steps(ctx, steps_list, only=["timeline"])
    assert all(result["status"] == "ok" for result in results), results

    mix_step = next(step for step in steps_list if step.name == "mix")
    result = mix_step.run(ctx)
    assert result.get("warnings") == []
    assert (root / "work" / "mix.wav").is_file()
    import wave

    with wave.open(str(root / "work" / "bed.wav"), "rb") as handle:
        frames = handle.getnframes()
        data = handle.readframes(frames)
    assert frames > 0
    assert max(data) > 0


def test_qa_fails_on_duration_mismatch(clone):
    from forja import errors, steps

    video = clone.root / "out" / "video.mp4"
    _ffmpeg(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x180:rate=30:duration=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-t",
            "1",
            str(video),
        ]
    )
    (clone.root / "out" / "qa.json").unlink(missing_ok=True)

    with pytest.raises(errors.ForjaError) as excinfo:
        steps.run_steps(clone.ctx, clone.steps, only=["qa"])
    error = excinfo.value
    assert error.code == "GATE_FAILED"
    issues = (error.details or {}).get("issues") or []
    assert any(issue.get("code") == "DURATION_MISMATCH" for issue in issues), issues


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


def test_voices_rejects_unsafe_scene_id_without_writing_outside(clone):
    import yaml

    from forja import errors

    path = clone.root / "storyboard.yaml"
    sb = yaml.safe_load(path.read_text(encoding="utf-8"))
    sb["scenes"][0]["id"] = "../../../PWNED"
    path.write_text(yaml.safe_dump(sb, sort_keys=False, allow_unicode=True), encoding="utf-8")

    voices = next(step for step in clone.steps if step.name == "voices")
    with pytest.raises(errors.ForjaError) as excinfo:
        voices.run(clone.ctx)
    assert excinfo.value.code == "CONFIG_INVALID"
    assert not (clone.root.parent / "PWNED.wav").exists()


def test_voices_files_provider_reads_project_wavs(clone):
    import yaml

    from forja import tts

    cfg_path = clone.root / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    cfg["voices"]["provider"] = "files"
    cfg["voices"]["input_dir"] = "voices"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (clone.root / "voices").mkdir(exist_ok=True)
    (clone.root / "voices" / "S1.wav").write_bytes(tts.mock_wav("teste"))

    ctx = _make_ctx(clone.root)
    voices = next(step for step in clone.steps if step.name == "voices")
    voices.run(ctx)
    manifest = _read_json(clone.root / "work" / "voices" / "manifest.json")
    assert set(manifest) == {"S1"}


def test_build_bed_mixes_clip_audio_and_mute_silences(assets, tmp_path):
    from forja import media, storyboard as storyboard_mod
    from forja.workflows import storyboard as workflow

    root = _new_project(tmp_path / "p", assets)
    clip_audio = root / "assets" / "clip-audio.mp4"
    _ffmpeg(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x90:rate=30:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2:sample_rate=48000",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(clip_audio),
        ]
    )
    ctx = _make_ctx(root)
    sb = _storyboard()
    sb["scenes"][0]["layers"] = [
        layer for layer in sb["scenes"][0]["layers"] if layer.get("type") != "music"
    ]
    timeline = {
        "total_s": 2.0,
        "scenes": [
            {
                "id": "S1",
                "start": 0.0,
                "end": 2.0,
                "layers": [
                    {
                        "type": "clip",
                        "file": "assets/clip-audio.mp4",
                        "start": 0.0,
                        "end": 2.0,
                        "audio": {"mode": "keep"},
                    }
                ],
            }
        ],
    }
    bed = root / "work" / "bed-clip.wav"
    workflow._build_bed(ctx, sb, timeline, 2.0, bed)
    import wave

    with wave.open(str(bed), "rb") as handle:
        data = handle.readframes(handle.getnframes())
    assert max(data) > 0

    timeline["scenes"][0]["layers"][0]["audio"] = {"mode": "mute"}
    muted = root / "work" / "bed-muted.wav"
    workflow._build_bed(ctx, sb, timeline, 2.0, muted)
    with wave.open(str(muted), "rb") as handle:
        data = handle.readframes(handle.getnframes())
    assert max(data) == 0


def test_timeline_resolves_word_anchor_with_transcription(monkeypatch, assets, tmp_path):
    from forja import steps
    from forja.workflows import storyboard as workflow

    root = _new_project(tmp_path / "p", assets)
    storyboard = _storyboard()
    storyboard["scenes"][0]["layers"].append(
        {
            "type": "card",
            "asset": "assets/card.png",
            "enter": {"anchor": "word", "word": "comeca"},
        }
    )
    _write_storyboard(root, storyboard)

    calls = []

    def fake_transcribe(wav, cfg, model_dir):
        calls.append((str(wav), cfg))
        return {
            "segments": [
                {
                    "words": [
                        {"word": "O", "start": 0.0, "end": 0.2},
                        {"word": "comeca", "start": 1.2, "end": 1.4},
                    ]
                }
            ]
        }

    monkeypatch.setattr(workflow.transcribe, "run_transcribe", fake_transcribe)
    ctx = _make_ctx(root)
    results = steps.run_steps(ctx, _storyboard_steps(), only=["voices", "timeline"])
    assert all(result["status"] == "ok" for result in results), results
    assert calls
    timeline = _read_json(root / "work" / "timeline.json")
    card = next(
        layer
        for layer in timeline["scenes"][0]["layers"]
        if layer.get("type") == "card" and layer.get("enter", {}).get("anchor") == "word"
    )
    assert card["start"] == pytest.approx(PAD_BEFORE + 1.2)
    assert not card.get("warnings")
