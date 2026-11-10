"""Contratos de regressao para ancoras por palavra (H1) e cache de ``voices`` (H2).

H1: o passo ``timeline`` nao pode alinhar no chute nem ignorar a ausencia do WAV
de narracao quando a cena usa ``enter/exit.anchor: word``. O fallback com
``warnings`` continua valendo apenas para a funcao pura ``resolve_timeline``.

H2: no provider padrao ``google_ai_studio`` (e no alias ``files``) os WAVs
fornecidos pelo usuario em ``voices/`` fazem parte das entradas do passo
``voices``. Nos demais providers o hash nao depende desses arquivos.

Os imports de ``forja`` ficam dentro dos helpers/testes, como nos testes de
workflow existentes: a coleta nao deve depender de corpos de passos.
"""

from __future__ import annotations

import io
import json
import shutil
import wave
from pathlib import Path

import pytest

_HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

PROVIDED_WAV_PROVIDERS = ("google_ai_studio", "files")
OTHER_PROVIDERS = ("piper", "gemini")


# --------------------------------------------------------------------- apoio


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

    (root / "storyboard.yaml").write_text(
        yaml.safe_dump(storyboard, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _storyboard(anchors: dict, narration: str = "um dois tres") -> dict:
    layer = {"type": "card", "asset": "assets/card.png"}
    layer.update(anchors)
    return {
        "version": 1,
        "canvas": {"w": 320, "h": 180, "fps": 30},
        "scenes": [
            {
                "id": "s1",
                "duration": {"fixed_s": 5.0, "pad_before": 0.3, "pad_after": 0.2},
                "layers": [
                    {"type": "narration", "text": narration, "lang": "pt-BR"},
                    layer,
                ],
            }
        ],
    }


def _new_storyboard_project(tmp_path: Path, anchors: dict, narration: str = "um dois tres") -> Path:
    from forja import project

    root = tmp_path / "p"
    project.scaffold(root, "demo", workflow="storyboard")
    (root / "assets").mkdir(parents=True, exist_ok=True)
    # O validate exige que o asset exista; a timeline nao abre a imagem.
    (root / "assets" / "card.png").write_bytes(b"png")
    _write_storyboard(root, _storyboard(anchors, narration=narration))
    return root


def _write_voice_cache(root: Path, scene_id: str = "s1", text: str = "um dois tres") -> None:
    """Cria o WAV de narracao e o manifesto que o passo ``timeline`` le."""
    from forja import tts

    voices = root / "work" / "voices"
    voices.mkdir(parents=True, exist_ok=True)
    wav_path = voices / (scene_id + ".wav")
    wav_path.write_bytes(tts.mock_wav(text))
    with wave.open(str(wav_path), "rb") as handle:
        duration = handle.getnframes() / float(handle.getframerate())
    manifest = {scene_id: {"wav": "work/voices/%s.wav" % scene_id, "duration": duration}}
    (voices / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )


def _workflow_steps(workflow_name: str):
    from forja import workflows
    from forja.workflows import dub as _dub  # noqa: F401  (registra)
    from forja.workflows import storyboard as _storyboard  # noqa: F401  (registra)

    return workflows.get_workflow(workflow_name).steps_factory()


def _step(root: Path, name: str):
    step = next(step for step in _workflow_steps("storyboard") if step.name == name)
    return step


def _fake_transcript(words):
    return {
        "segments": [
            {
                "words": [
                    {"word": text, "start": start, "end": start + 0.1}
                    for text, start in words
                ]
            }
        ]
    }


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------- H1: ancora por palavra


@pytest.mark.parametrize("anchor_key", ["enter", "exit"])
def test_timeline_unresolved_word_anchor_fails_with_missing_prereq(
    monkeypatch, tmp_path, anchor_key
):
    from forja import errors

    root = _new_storyboard_project(
        tmp_path, {anchor_key: {"anchor": "word", "word": "banana"}}
    )
    _write_voice_cache(root)

    from forja.workflows import storyboard as workflow

    monkeypatch.setattr(
        workflow.transcribe,
        "run_transcribe",
        lambda *args, **kwargs: _fake_transcript([("um", 0.0), ("dois", 1.2)]),
    )

    timeline_step = _step(root, "timeline")
    with pytest.raises(errors.ForjaError) as excinfo:
        timeline_step.run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "MISSING_PREREQ"
    assert error.exit_code == 4
    details = error.details or {}
    assert details.get("scene") == "s1"
    assert details.get("word") == "banana"

    hint = (error.hint or "").lower()
    assert hint and (
        "word" in hint or "palavra" in hint or "ancora" in hint or "âncora" in hint
    )

    # O alinhamento no chute nunca pode virar timeline.json.
    assert not (root / "work" / "timeline.json").exists()


def test_timeline_empty_word_anchor_fails_with_missing_prereq(monkeypatch, tmp_path):
    from forja import errors

    root = _new_storyboard_project(
        tmp_path, {"enter": {"anchor": "word", "word": ""}}
    )
    _write_voice_cache(root)

    from forja.workflows import storyboard as workflow

    monkeypatch.setattr(
        workflow.transcribe,
        "run_transcribe",
        lambda *args, **kwargs: _fake_transcript([("um", 0.0), ("dois", 1.2)]),
    )

    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "MISSING_PREREQ"
    assert error.exit_code == 4
    assert (error.details or {}).get("scene") == "s1"
    assert (error.details or {}).get("word") == ""
    assert not (root / "work" / "timeline.json").exists()


def test_timeline_missing_narration_wav_fails_with_missing_prereq(monkeypatch, tmp_path):
    from forja import errors

    root = _new_storyboard_project(
        tmp_path, {"enter": {"anchor": "word", "word": "dois"}}
    )
    # O manifesto existe, mas o WAV da narracao foi removido/nao foi gerado:
    # antes o passo pulava a cena em silencio.
    _write_json(
        root / "work" / "voices" / "manifest.json",
        {"s1": {"wav": "work/voices/s1.wav", "duration": 3.0}},
    )
    from forja.workflows import storyboard as workflow

    monkeypatch.setattr(
        workflow.transcribe,
        "run_transcribe",
        lambda *args, **kwargs: _fake_transcript([("dois", 1.2)]),
    )

    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "MISSING_PREREQ"
    assert error.exit_code == 4
    assert not (root / "work" / "timeline.json").exists()


def test_timeline_resolved_word_anchor_uses_word_time_pad_and_offset(
    monkeypatch, tmp_path
):
    from forja.workflows import storyboard as workflow

    root = _new_storyboard_project(
        tmp_path,
        {
            "enter": {"anchor": "word", "word": "dois", "offset_s": 0.25},
            "exit": {"anchor": "word", "word": "tres", "offset_s": 0.10},
        },
    )
    _write_voice_cache(root)

    monkeypatch.setattr(
        workflow.transcribe,
        "run_transcribe",
        lambda *args, **kwargs: _fake_transcript(
            [("um", 0.0), ("dois", 1.2), ("tres", 2.5)]
        ),
    )

    _step(root, "timeline").run(_make_ctx(root))

    timeline = json.loads(
        (root / "work" / "timeline.json").read_text(encoding="utf-8")
    )
    card = next(
        layer
        for layer in timeline["scenes"][0]["layers"]
        if layer.get("type") == "card"
    )
    assert card["start"] == pytest.approx(0.3 + 1.2 + 0.25)
    assert card["end"] == pytest.approx(0.3 + 2.5 + 0.10)
    assert not card.get("warnings")


def test_timeline_without_word_anchor_does_not_transcribe(monkeypatch, tmp_path):
    root = _new_storyboard_project(tmp_path, {"enter": {"anchor": "scene_start"}})
    _write_voice_cache(root)

    from forja.workflows import storyboard as workflow

    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("nao deveria transcrever cena sem ancora por palavra")

    monkeypatch.setattr(workflow.transcribe, "run_transcribe", forbidden)

    _step(root, "timeline").run(_make_ctx(root))

    assert calls == []
    assert (root / "work" / "timeline.json").is_file()


# --------------------------------------------------------- H2: cache de voices


def _configure_provider(root: Path, provider: str) -> None:
    import yaml

    from forja import config

    cfg_path = root / "config.yaml"
    cfg = config.load_config(cfg_path)
    cfg["voices"]["provider"] = provider
    cfg["voices"]["input_dir"] = "voices"
    cfg_path.write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def _new_dub_project(tmp_path: Path, provider: str) -> Path:
    from forja import project, tts

    root = tmp_path / "p"
    project.scaffold(root, "demo", workflow="dub")
    _configure_provider(root, provider)
    cues = [
        {
            "id": "A",
            "role": "narrator",
            "t0": 0.5,
            "t1": 3.5,
            "text": "Aqui comeca tudo.",
        }
    ]
    _write_json(root / "cues.json", cues)
    (root / "lower_thirds.json").write_text("[]\n", encoding="utf-8")
    (root / "voices").mkdir(exist_ok=True)
    (root / "voices" / "A.wav").write_bytes(tts.mock_wav("Aqui comeca tudo."))
    return root


def _new_storyboard_provider_project(tmp_path: Path, provider: str) -> Path:
    from forja import project, tts

    root = tmp_path / "p"
    project.scaffold(root, "demo", workflow="storyboard")
    _configure_provider(root, provider)
    (root / "assets").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "card.png").write_bytes(b"png")
    _write_storyboard(
        root,
        {
            "version": 1,
            "canvas": {"w": 320, "h": 180, "fps": 30},
            "scenes": [
                {
                    "id": "s1",
                    "duration": {"fixed_s": 5.0},
                    "layers": [
                        {"type": "narration", "text": "um dois tres", "lang": "pt-BR"}
                    ],
                }
            ],
        },
    )
    (root / "voices").mkdir(exist_ok=True)
    (root / "voices" / "s1.wav").write_bytes(tts.mock_wav("um dois tres"))
    return root


def _run_cli(argv):
    from forja import cli

    out = io.StringIO()
    err = io.StringIO()
    code = cli.main(argv, env={}, out=out, err=err)
    text = out.getvalue()
    document = json.loads(text) if text.strip() else None
    return code, document, err.getvalue()


def _run_only_voices(root: Path):
    code, document, err = _run_cli(
        ["--json", "--project", str(root), "run", "--only", "voices"]
    )
    assert code == 0, (document, err)
    return {entry["step"]: entry for entry in document["data"]["steps"]}


def _status(root: Path):
    code, document, err = _run_cli(
        ["--json", "--project", str(root), "status"]
    )
    assert code == 0, (document, err)
    return {entry["name"]: entry for entry in document["steps"]}


def _assert_voices_cache_tracks_provided_wav(root: Path, scene_id: str) -> None:
    from forja import tts

    work_wav = root / "work" / "voices" / (scene_id + ".wav")

    first = _run_only_voices(root)
    assert first["voices"]["status"] == "ok", first
    assert _status(root)["voices"]["state"] == "fresh"
    assert _run_only_voices(root)["voices"]["status"] == "skipped"

    before = work_wav.read_bytes()
    (root / "voices" / (scene_id + ".wav")).write_bytes(
        tts.mock_wav("uma frase completamente diferente e bem mais longa")
    )

    assert _status(root)["voices"]["state"] == "stale"
    rerun = _run_only_voices(root)
    assert rerun["voices"]["status"] == "ok", rerun
    assert work_wav.read_bytes() != before

    assert _status(root)["voices"]["state"] == "fresh"
    assert _run_only_voices(root)["voices"]["status"] == "skipped"


@pytest.mark.skipif(
    not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH"
)
@pytest.mark.parametrize("provider", PROVIDED_WAV_PROVIDERS)
def test_storyboard_voices_cache_invalidates_when_provided_wav_changes(
    tmp_path, provider
):
    root = _new_storyboard_provider_project(tmp_path, provider)
    _assert_voices_cache_tracks_provided_wav(root, "s1")


@pytest.mark.skipif(
    not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH"
)
@pytest.mark.parametrize("provider", PROVIDED_WAV_PROVIDERS)
def test_dub_voices_cache_invalidates_when_provided_wav_changes(tmp_path, provider):
    root = _new_dub_project(tmp_path, provider)
    _assert_voices_cache_tracks_provided_wav(root, "A")


@pytest.mark.parametrize("provider", OTHER_PROVIDERS)
def test_storyboard_voices_hash_ignores_user_wav_for_other_providers(
    tmp_path, provider
):
    from forja import cache, tts

    root = _new_storyboard_provider_project(tmp_path, provider)
    ctx = _make_ctx(root)
    voices_step = next(
        step for step in _workflow_steps("storyboard") if step.name == "voices"
    )
    paths, extra = voices_step.inputs(ctx)
    before = cache.hash_inputs(paths, extra)

    (root / "voices" / "s1.wav").write_bytes(
        tts.mock_wav("outra frase completamente diferente e mais longa")
    )
    paths, extra = voices_step.inputs(ctx)
    assert cache.hash_inputs(paths, extra) == before


@pytest.mark.parametrize("provider", OTHER_PROVIDERS)
def test_dub_voices_hash_ignores_user_wav_for_other_providers(tmp_path, provider):
    from forja import cache, tts

    root = _new_dub_project(tmp_path, provider)
    ctx = _make_ctx(root)
    voices_step = next(
        step for step in _workflow_steps("dub") if step.name == "voices"
    )
    paths, extra = voices_step.inputs(ctx)
    before = cache.hash_inputs(paths, extra)

    (root / "voices" / "A.wav").write_bytes(
        tts.mock_wav("outra frase completamente diferente e mais longa")
    )
    paths, extra = voices_step.inputs(ctx)
    assert cache.hash_inputs(paths, extra) == before
