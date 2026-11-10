"""Contrato da rodada 2 da auditoria (A1-A5).

Esta lane escreve apenas o contrato: os testes abaixo descrevem o comportamento
corrigido e devem falhar no codigo atual. Nenhum teste edita ``forja/``.

- A1: ``sfx`` com ``enter`` resolve o inicio pela mesma ``_layer_start`` das
  demais camadas (palavra, ``at_s``, ``scene_start``/``scene_end``, offset);
  ``sfx.start`` numerico junto de ``enter`` e erro ``SFX_START_AND_ENTER``; no
  passo ``timeline`` toda ancora ``word`` e verificada, mesmo sem ``warnings``.
- A2: depois da timeline resolvida, ``sfx.start`` absoluto fora da cena (inclusive
  ``from: narration``) e erro ``CONFIG_INVALID`` antes de gravar ``timeline.json``.
- A3: ``sfx.start`` presente e nao numerico e erro ``SFX_START`` no validate.
- A4: ids duplicados sao ``DUPLICATE_SCENE_ID`` e a checagem de ancoras compara
  camadas pela posicao da cena, nunca por ``scene.id``.
- A5: a tabela de troubleshooting e o README citam o passo ``timeline`` e a
  narracao/WAV ausente como origem de ``MISSING_PREREQ``.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import wave
from pathlib import Path

import pytest

_HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

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


# ------------------------------------------------------------- A1: resolve


def test_resolve_timeline_sfx_enter_word_uses_word_time_pad_and_offset():
    from forja import storyboard

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 5.0, "pad_before": 0.3},
            [
                _narration("um dois tres"),
                _sfx(enter={"anchor": "word", "word": "dois", "offset_s": 0.25}),
            ],
        )
    )
    words = {"s1": [{"word": "dois", "start": 1.2, "end": 1.4}]}
    timeline = storyboard.resolve_timeline(sb, {"s1": 3.0}, words=words)
    layer = timeline["scenes"][0]["layers"][1]

    assert layer["type"] == "sfx"
    assert layer["start"] == pytest.approx(0.3 + 1.2 + 0.25)
    assert not layer.get("warnings")


def test_resolve_timeline_sfx_enter_missing_word_warns_and_falls_back_to_scene_start():
    from forja import storyboard

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 5.0},
            [_sfx(enter={"anchor": "word", "word": "banana"})],
        )
    )
    words = {"s1": [{"word": "dois", "start": 1.2, "end": 1.4}]}
    timeline = storyboard.resolve_timeline(sb, {"s1": 3.0}, words=words)
    layer = timeline["scenes"][0]["layers"][0]

    assert layer["start"] == pytest.approx(0.0)
    warnings = layer.get("warnings") or []
    assert warnings, "sfx com ancora word nao resolvida precisa avisar como as demais camadas"
    assert any("banana" in str(message) for message in warnings), warnings


@pytest.mark.parametrize(
    "enter, expected",
    [
        ({"anchor": "at_s", "at_s": 0.75}, 0.75),
        ({"anchor": "scene_start", "offset_s": 0.2}, 0.2),
        ({"anchor": "scene_end", "offset_s": -0.5}, 4.5),
    ],
)
def test_resolve_timeline_sfx_enter_non_word_anchors(enter, expected):
    from forja import storyboard

    sb = _sb(
        _scene("s1", {"fixed_s": 5.0}, [_sfx(enter=enter)]),
    )
    timeline = storyboard.resolve_timeline(sb, {"s1": 3.0})
    layer = timeline["scenes"][0]["layers"][0]

    assert layer["start"] == pytest.approx(expected)


def test_resolve_timeline_sfx_numeric_start_still_relative_and_card_anchor_unchanged():
    from forja import storyboard

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 5.0, "pad_before": 0.3},
            [
                _sfx(start=1.0),
                _card(enter={"anchor": "word", "word": "dois"}),
            ],
        )
    )
    words = {"s1": [{"word": "dois", "start": 1.2, "end": 1.4}]}
    timeline = storyboard.resolve_timeline(sb, {"s1": 3.0}, words=words)
    sfx_layer, card_layer = timeline["scenes"][0]["layers"]

    assert sfx_layer["start"] == pytest.approx(1.0)
    assert card_layer["start"] == pytest.approx(0.3 + 1.2)
    assert not sfx_layer.get("warnings")
    assert not card_layer.get("warnings")


# --------------------------------------------------- A1: validate e workflow


@pytest.mark.parametrize(
    "enter",
    [
        {"anchor": "word", "word": "dois"},
        {"anchor": "at_s", "at_s": 0.5},
        {"anchor": "scene_start"},
    ],
)
def test_validate_sfx_numeric_start_with_enter_is_ambiguous(enter):
    from forja import storyboard

    sb = _sb(_scene("s1", {"fixed_s": 2.0}, [_sfx(start=1.0, enter=enter)]))
    issues = storyboard.validate_storyboard(sb)
    matched = _issues(issues, "SFX_START_AND_ENTER")

    assert matched, issues
    assert matched[0]["level"] == "error", matched[0]


def test_validate_sfx_without_enter_keeps_numeric_start_valid():
    from forja import storyboard

    sb = _sb(_scene("s1", {"fixed_s": 2.0}, [_sfx(start=1.0)]))
    issues = storyboard.validate_storyboard(sb)

    assert not _errors(issues), issues
    assert not _issues(issues, "SFX_START_AND_ENTER"), issues


def test_timeline_sfx_word_anchor_uses_real_word_time(monkeypatch, tmp_path):
    from forja.workflows import storyboard as workflow

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 5.0, "pad_before": 0.3, "pad_after": 0.2},
            [
                _narration("um dois tres"),
                _sfx(enter={"anchor": "word", "word": "dois", "offset_s": 0.25}),
            ],
        )
    )
    root = _new_storyboard_project(tmp_path, sb)
    _write_voice_cache(root, {"s1": 3.0})

    monkeypatch.setattr(
        workflow.transcribe,
        "run_transcribe",
        lambda *args, **kwargs: _fake_transcript([("um", 0.0), ("dois", 1.2)]),
    )

    _step(root, "timeline").run(_make_ctx(root))

    timeline = json.loads(
        (root / "work" / "timeline.json").read_text(encoding="utf-8")
    )
    sfx_layer = next(
        layer for layer in timeline["scenes"][0]["layers"] if layer["type"] == "sfx"
    )
    assert sfx_layer["start"] == pytest.approx(0.3 + 1.2 + 0.25)
    assert not sfx_layer.get("warnings")


def test_timeline_sfx_missing_word_anchor_fails_before_writing_timeline(
    monkeypatch, tmp_path
):
    from forja import errors
    from forja.workflows import storyboard as workflow

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 5.0, "pad_before": 0.3},
            [
                _narration("um dois tres"),
                _sfx(enter={"anchor": "word", "word": "banana"}),
            ],
        )
    )
    root = _new_storyboard_project(tmp_path, sb)
    _write_voice_cache(root, {"s1": 3.0})

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
    details = error.details or {}
    assert details.get("scene") == "s1"
    assert details.get("word") == "banana"
    assert not (root / "work" / "timeline.json").exists()


# --------------------------------------- A2: sfx fora de cena por narracao


def _narration_storyboard(sfx_start):
    return _sb(
        _scene(
            "s1",
            {"from": "narration", "pad_before": 0.0, "pad_after": 0.0},
            [_narration("cena um"), _sfx(start=sfx_start)],
        ),
        _scene(
            "s2",
            {"from": "narration", "pad_before": 0.0, "pad_after": 0.0},
            [_narration("cena dois")],
        ),
    )


def test_timeline_sfx_start_outside_narration_scene_fails_config_invalid(tmp_path):
    from forja import errors

    root = _new_storyboard_project(tmp_path, _narration_storyboard(3.0))
    _write_voice_cache(root, {"s1": 2.0, "s2": 2.0})

    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "CONFIG_INVALID"
    details = error.details or {}
    assert details.get("scene") == "s1"
    assert float(details.get("start")) == pytest.approx(3.0)
    assert float(details.get("scene_start")) == pytest.approx(0.0)
    assert float(details.get("scene_end")) == pytest.approx(2.0)
    hint = (error.hint or "").lower()
    assert hint and any(
        token in hint for token in ("sfx", "cena", "start")
    ), error.hint
    assert not (root / "work" / "timeline.json").exists()


def test_timeline_sfx_start_at_narration_scene_end_fails_config_invalid(tmp_path):
    from forja import errors

    root = _new_storyboard_project(tmp_path, _narration_storyboard(2.0))
    _write_voice_cache(root, {"s1": 2.0, "s2": 2.0})

    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    assert excinfo.value.code == "CONFIG_INVALID"
    assert not (root / "work" / "timeline.json").exists()


def test_timeline_sfx_start_inside_narration_scene_is_written(tmp_path):
    root = _new_storyboard_project(tmp_path, _narration_storyboard(1.0))
    _write_voice_cache(root, {"s1": 2.0, "s2": 2.0})

    _step(root, "timeline").run(_make_ctx(root))

    timeline = json.loads(
        (root / "work" / "timeline.json").read_text(encoding="utf-8")
    )
    sfx_layer = next(
        layer for layer in timeline["scenes"][0]["layers"] if layer["type"] == "sfx"
    )
    assert sfx_layer["start"] == pytest.approx(1.0)


# --------------------------------------------------------- A3: tipo do start


@pytest.mark.parametrize("start", ["1.0", True, [1.0], None])
def test_validate_sfx_start_present_but_not_numeric_is_error(start):
    from forja import storyboard

    layer = _sfx()
    layer["start"] = start
    assert "start" in layer

    sb = _sb(_scene("s1", {"fixed_s": 2.0}, [layer]))
    issues = storyboard.validate_storyboard(sb)
    matched = _issues(issues, "SFX_START")

    assert matched, issues
    assert matched[0]["level"] == "error", matched[0]


@pytest.mark.parametrize("start", [0, 0.5, 1, 1.5])
def test_validate_sfx_numeric_start_stays_valid(start):
    from forja import storyboard

    sb = _sb(_scene("s1", {"fixed_s": 2.0}, [_sfx(start=start)]))
    issues = storyboard.validate_storyboard(sb)

    assert not _issues(issues, "SFX_START"), issues
    assert not _errors(issues), issues


def test_validate_sfx_fixed_scene_start_at_end_still_errors():
    from forja import storyboard

    sb = _sb(_scene("s1", {"fixed_s": 2.0}, [_sfx(start=2.0)]))
    issues = storyboard.validate_storyboard(sb)

    assert _issues(issues, "SFX_START"), issues
    assert _errors(issues), issues


# --------------------------------------------- A4: ids duplicados e posicao


def test_validate_duplicate_scene_id_uses_duplicate_scene_id_code():
    from forja import storyboard

    sb = _sb(
        _scene("s1", {"fixed_s": 2.0}, []),
        _scene("s1", {"fixed_s": 2.0}, []),
    )
    issues = storyboard.validate_storyboard(sb)
    matched = _issues(issues, "DUPLICATE_SCENE_ID")

    assert matched, issues
    assert matched[0]["level"] == "error", matched[0]


def test_timeline_duplicate_scene_ids_do_not_mask_missing_word_anchor(
    monkeypatch, tmp_path
):
    from forja import errors
    from forja.workflows import storyboard as workflow

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 5.0, "pad_before": 0.3},
            [
                _narration("um dois tres"),
                _card(enter={"anchor": "word", "word": "banana"}),
            ],
        ),
        _scene(
            "s1",
            {"fixed_s": 5.0, "pad_before": 0.3},
            [
                _narration("um dois tres"),
                _card(enter={"anchor": "word", "word": "dois"}),
            ],
        ),
    )
    root = _new_storyboard_project(tmp_path, sb)
    _write_voice_cache(root, {"s1": 3.0})

    monkeypatch.setattr(
        workflow.transcribe,
        "run_transcribe",
        lambda *args, **kwargs: _fake_transcript([("um", 0.0), ("dois", 1.2)]),
    )

    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "MISSING_PREREQ"
    details = error.details or {}
    assert details.get("scene") == "s1"
    assert details.get("word") == "banana"
    assert not (root / "work" / "timeline.json").exists()


# ---------------------------------------------------------------- A5: docs


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _plain_html(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _missing_prereq_rows(text: str):
    rows = re.findall(r"<tr\b[^>]*>.*?</tr>", text, flags=re.IGNORECASE | re.DOTALL)
    return [row for row in rows if "MISSING_PREREQ" in row]


def test_docs_troubleshooting_mentions_timeline_word_anchor_and_wav():
    text = (_repo_root() / "docs" / "index.html").read_text(encoding="utf-8")
    rows = _missing_prereq_rows(text)
    assert rows, "docs/index.html precisa da linha MISSING_PREREQ na tabela de erros"

    guidance = " ".join(_plain_html(row) for row in rows).lower()
    assert "timeline" in guidance, guidance
    assert "palavra" in guidance or "ância" in guidance or "ancora" in guidance, guidance
    assert "wav" in guidance or "narra" in guidance, guidance


def test_readme_mentions_timeline_word_anchor_and_narration_wav_for_missing_prereq():
    text = (_repo_root() / "README.md").read_text(encoding="utf-8")
    paragraphs = [
        re.sub(r"\s+", " ", paragraph)
        for paragraph in re.split(r"\n\s*\n", text)
        if "MISSING_PREREQ" in paragraph
    ]
    assert paragraphs, "README.md precisa citar MISSING_PREREQ"

    guidance = " ".join(paragraphs).lower()
    assert "timeline" in guidance, guidance
    assert "palavra" in guidance or "ância" in guidance or "ancora" in guidance, guidance
    has_wav = "wav" in guidance
    has_missing_narration = (
        ("falta" in guidance or "ausente" in guidance or "sem " in guidance)
        and ("narra" in guidance)
    )
    assert has_wav or has_missing_narration, guidance


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_timeline_resolved_sfx_start_feeds_audio_plan(tmp_path):
    """Sem regressao do bed: o start resolvido da timeline chega ao plano de audio."""
    from forja import storyboard
    from forja.workflows import storyboard as workflow

    sb = _sb(_scene("s1", {"fixed_s": 2.0}, [_sfx(start=1.0)]))
    root = _new_storyboard_project(tmp_path, sb)
    timeline = storyboard.resolve_timeline(sb, {})
    plan = workflow._audio_plan(_make_ctx(root), sb, timeline, 2.0)
    sfx_items = [item for item in plan if item.get("kind") == "sfx"]

    assert sfx_items, plan
    assert sfx_items[0]["start"] == pytest.approx(1.0)
