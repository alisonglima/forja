"""Contrato da rodada 4 da auditoria (A1, M1, B1, B2).

Esta lane escreve apenas o contrato: os testes abaixo descrevem o comportamento
corrigido e devem falhar no codigo atual. Nenhum teste edita ``forja/``.

- A1: o fim efetivo de um ``sfx`` no bed e sempre limitado ao ``scene_end`` da
  cena em que ele foi declarado, qualquer que seja a origem (``duration``,
  ``exit.at_s``, ``exit.anchor``, ``hold_s``); fim nao finito cai em
  ``scene_end``. A timeline continua gravando o ``end`` resolvido como esta.
- M1: ``sfx.duration`` nao finito e ``SFX_DURATION``; ``hold_s`` /
  ``enter.at_s`` / ``enter.offset_s`` / ``exit.at_s`` / ``exit.offset_s`` nao
  finitos em qualquer camada sao ``LAYER_TIMING``.
- B1: ids ausente (``None``) e vazio (``""``) contam como o mesmo id vazio no
  check de duplicados do passo ``timeline``.
- B2: o hint de ``enter`` fora da cena so fala "no fim da cena" quando a
  ancora e ``scene_end``; nas demais cita o valor resolvido e o intervalo.
"""

from __future__ import annotations

import pytest

from tests.test_fix_round3 import (
    _HAS_FFMPEG,
    _bed,
    _errors,
    _fake_transcript,
    _issues,
    _make_ctx,
    _make_sfx,
    _narration,
    _new_storyboard_project,
    _rms,
    _sb,
    _scene,
    _sfx,
    _sfx_item,
    _step,
    _write_voice_cache,
)

_NAN = float("nan")
_INF = float("inf")
_NINF = float("-inf")


# --------------------------------------------------------------------- apoio


def _padded_scene(layer, scene_id="s1", fixed_s=2.0):
    return _scene(scene_id, {"fixed_s": fixed_s}, [layer])


def _two_scenes(layer):
    sb = _sb(
        _padded_scene(layer),
        _scene("s2", {"fixed_s": 2.0}, []),
    )
    return sb


def _bed_from_layer(tmp_path, layer, name, words=None):
    """Monta o bed real (ffmpeg) de uma cena de 2 s seguida de outra de 2 s."""
    from forja import storyboard

    sb = _two_scenes(layer)
    root = _new_storyboard_project(tmp_path, sb)
    _make_sfx(root / "assets" / "sfx.wav", frequency=700, duration=6.0)
    timeline = storyboard.resolve_timeline(sb, {}, words=words or {})
    rate, samples = _bed(root, sb, timeline, name)
    return rate, samples, timeline


def _assert_tone_scene_one_only(rate, samples):
    assert _rms(samples[int(0.10 * rate) : int(1.90 * rate)]) > 0.05
    assert _rms(samples[int(2.10 * rate) : int(3.90 * rate)]) < 0.005


def _timeline_layer(layer, words=None):
    from forja import storyboard

    sb = _two_scenes(layer)
    timeline = storyboard.resolve_timeline(sb, {}, words=words or {})
    return sb, timeline, timeline["scenes"][0]["layers"][0]


def _empty_id_label(value):
    """Representacoes legiveis aceitaveis para o id vazio em ``details.scene``."""
    text = str(value).strip().lower()
    if text == "none":
        return False
    return (
        text == ""
        or "vazio" in text
        or "sem id" in text
        or "ausente" in text
    )


# -------------------------------------- A1: plano de audio limitado a cena


def test_audio_plan_sfx_exit_at_s_beyond_scene_is_clamped(tmp_path):
    layer = _sfx(
        duration=5.0,
        enter={"anchor": "scene_start"},
        exit={"anchor": "at_s", "at_s": 3.0},
    )
    sb, timeline, resolved = _timeline_layer(layer)
    assert resolved["end"] == pytest.approx(3.0), "a timeline grava o end resolvido"

    item = _sfx_item(_new_storyboard_project(tmp_path, sb), sb, timeline)
    assert item["start"] == pytest.approx(0.0)
    assert item["duration"] == pytest.approx(2.0)


def test_audio_plan_sfx_exit_scene_end_offset_is_clamped(tmp_path):
    layer = _sfx(
        duration=5.0,
        enter={"anchor": "scene_start"},
        exit={"anchor": "scene_end", "offset_s": 1.0},
    )
    sb, timeline, resolved = _timeline_layer(layer)
    assert resolved["end"] == pytest.approx(3.0)

    item = _sfx_item(_new_storyboard_project(tmp_path, sb), sb, timeline)
    assert item["duration"] == pytest.approx(2.0)


def test_audio_plan_sfx_exit_word_offset_is_clamped(tmp_path):
    layer = _sfx(
        duration=5.0,
        enter={"anchor": "scene_start"},
        exit={"anchor": "word", "word": "dois", "offset_s": 0.5},
    )
    words = {"s1": [{"word": "dois", "start": 1.8, "end": 1.9}]}
    sb, timeline, resolved = _timeline_layer(layer, words=words)
    assert resolved["end"] == pytest.approx(2.3)

    item = _sfx_item(_new_storyboard_project(tmp_path, sb), sb, timeline)
    assert item["duration"] == pytest.approx(2.0)


def test_audio_plan_sfx_hold_s_beyond_scene_is_clamped(tmp_path):
    layer = _sfx(duration=5.0, enter={"anchor": "scene_start"}, hold_s=3.0)
    sb, timeline, resolved = _timeline_layer(layer)
    assert resolved["end"] == pytest.approx(3.0)

    item = _sfx_item(_new_storyboard_project(tmp_path, sb), sb, timeline)
    assert item["duration"] == pytest.approx(2.0)


@pytest.mark.parametrize("end", [_NAN, _INF], ids=["nan", "inf"])
def test_audio_plan_sfx_hold_s_non_finite_is_clamped(tmp_path, end):
    layer = _sfx(duration=5.0, enter={"anchor": "scene_start"}, hold_s=end)
    sb, timeline, _resolved = _timeline_layer(layer)

    item = _sfx_item(_new_storyboard_project(tmp_path, sb), sb, timeline)
    assert item["duration"] == pytest.approx(2.0)


@pytest.mark.parametrize("at_s", [_NAN, _INF], ids=["nan", "inf"])
def test_audio_plan_sfx_exit_at_s_non_finite_is_clamped(tmp_path, at_s):
    layer = _sfx(
        duration=5.0,
        enter={"anchor": "scene_start"},
        exit={"anchor": "at_s", "at_s": at_s},
    )
    sb, timeline, _resolved = _timeline_layer(layer)

    item = _sfx_item(_new_storyboard_project(tmp_path, sb), sb, timeline)
    assert item["duration"] == pytest.approx(2.0)


def test_audio_plan_sfx_duration_and_exit_beyond_scene_are_clamped(tmp_path):
    layer = _sfx(
        duration=5.0,
        enter={"anchor": "scene_start", "offset_s": 0.5},
        exit={"anchor": "at_s", "at_s": 3.0},
    )
    sb, timeline, resolved = _timeline_layer(layer)
    assert resolved["start"] == pytest.approx(0.5)
    assert resolved["end"] == pytest.approx(3.0)

    item = _sfx_item(_new_storyboard_project(tmp_path, sb), sb, timeline)
    assert item["duration"] == pytest.approx(1.5)


def test_audio_plan_sfx_duration_beyond_scene_is_limited(tmp_path):
    layer = _sfx(duration=5.0, enter={"anchor": "scene_start", "offset_s": 0.5})
    sb, timeline, resolved = _timeline_layer(layer)
    assert resolved["end"] == pytest.approx(2.0)

    item = _sfx_item(_new_storyboard_project(tmp_path, sb), sb, timeline)
    assert item["duration"] == pytest.approx(1.5)


def test_audio_plan_sfx_inside_scene_keeps_duration_and_music_clip(monkeypatch, tmp_path):
    """Sem regressao: sfx dentro da cena, duration menor que o exit, music/clip iguais."""
    from forja.workflows import storyboard as workflow

    sb = _sb(
        _scene(
            "s1",
            {"fixed_s": 4.0},
            [
                {
                    "type": "music",
                    "track": "assets/music.wav",
                    "gain_db": -6,
                    "license": {"kind": "cc0"},
                },
                {
                    "type": "clip",
                    "file": "assets/clip.mp4",
                    "audio": {"mode": "keep", "gain_db": -2},
                },
                _sfx(
                    duration=0.5,
                    enter={"anchor": "scene_start"},
                    exit={"anchor": "at_s", "at_s": 1.0},
                ),
            ],
        )
    )
    root = _new_storyboard_project(tmp_path, sb)
    (root / "assets" / "music.wav").write_bytes(b"RIFF")
    (root / "assets" / "clip.mp4").write_bytes(b"mp4")
    monkeypatch.setattr(workflow.probe, "probe_video", lambda _path: {"has_audio": True})

    timeline = workflow.storyboard_mod.resolve_timeline(sb, {})
    plan = workflow._audio_plan(_make_ctx(root), sb, timeline, timeline["total_s"])
    by_kind = {item["kind"]: item for item in plan}

    assert by_kind["music"]["duration"] == pytest.approx(4.0)
    assert by_kind["music"]["start"] == pytest.approx(0.0)
    assert by_kind["clip"]["duration"] == pytest.approx(4.0)
    assert by_kind["clip"]["start"] == pytest.approx(0.0)
    assert by_kind["sfx"]["start"] == pytest.approx(0.0)
    assert by_kind["sfx"]["duration"] == pytest.approx(0.5)


# ----------------------------------- A1: o corte provado no bed (ffmpeg real)


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_audio_bed_sfx_exit_at_s_beyond_scene_does_not_bleed(tmp_path):
    layer = _sfx(
        duration=5.0,
        enter={"anchor": "scene_start"},
        exit={"anchor": "at_s", "at_s": 3.0},
    )
    rate, samples, _timeline = _bed_from_layer(tmp_path, layer, "bed-exit-at-s.wav")
    _assert_tone_scene_one_only(rate, samples)


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_audio_bed_sfx_exit_scene_end_offset_does_not_bleed(tmp_path):
    layer = _sfx(
        duration=5.0,
        enter={"anchor": "scene_start"},
        exit={"anchor": "scene_end", "offset_s": 1.0},
    )
    rate, samples, _timeline = _bed_from_layer(tmp_path, layer, "bed-exit-scene-end.wav")
    _assert_tone_scene_one_only(rate, samples)


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_audio_bed_sfx_exit_word_offset_does_not_bleed(tmp_path):
    layer = _sfx(
        duration=5.0,
        enter={"anchor": "scene_start"},
        exit={"anchor": "word", "word": "dois", "offset_s": 0.5},
    )
    words = {"s1": [{"word": "dois", "start": 1.8, "end": 1.9}]}
    rate, samples, _timeline = _bed_from_layer(
        tmp_path, layer, "bed-exit-word.wav", words=words
    )
    _assert_tone_scene_one_only(rate, samples)


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_audio_bed_sfx_hold_s_beyond_scene_does_not_bleed(tmp_path):
    layer = _sfx(duration=5.0, enter={"anchor": "scene_start"}, hold_s=3.0)
    rate, samples, _timeline = _bed_from_layer(tmp_path, layer, "bed-hold-3.wav")
    _assert_tone_scene_one_only(rate, samples)


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_audio_bed_sfx_hold_s_inf_does_not_bleed(tmp_path):
    layer = _sfx(duration=5.0, enter={"anchor": "scene_start"}, hold_s=_INF)
    rate, samples, _timeline = _bed_from_layer(tmp_path, layer, "bed-hold-inf.wav")
    _assert_tone_scene_one_only(rate, samples)


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_audio_bed_sfx_exit_at_s_inf_does_not_bleed(tmp_path):
    layer = _sfx(
        duration=5.0,
        enter={"anchor": "scene_start"},
        exit={"anchor": "at_s", "at_s": _INF},
    )
    rate, samples, _timeline = _bed_from_layer(tmp_path, layer, "bed-exit-inf.wav")
    _assert_tone_scene_one_only(rate, samples)


@pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg/ffprobe nao encontrados no PATH")
def test_audio_bed_sfx_duration_5_is_limited_by_scene(tmp_path):
    layer = _sfx(duration=5.0, enter={"anchor": "scene_start", "offset_s": 0.5})
    rate, samples, _timeline = _bed_from_layer(tmp_path, layer, "bed-duration-5.wav")
    assert _rms(samples[int(0.60 * rate) : int(1.90 * rate)]) > 0.05
    assert _rms(samples[int(0.10 * rate) : int(0.40 * rate)]) < 0.005
    assert _rms(samples[int(2.10 * rate) : int(3.90 * rate)]) < 0.005


# ------------------------------------------- M1: duracao e timing finitos


@pytest.mark.parametrize(
    "duration",
    [_NAN, _INF, _NINF, 0, -1],
    ids=["nan", "inf", "menos_inf", "zero", "negativo"],
)
def test_validate_sfx_duration_non_finite_or_non_positive_is_error(duration):
    from forja import storyboard

    sb = _sb(_padded_scene(_sfx(duration=duration)))
    issues = storyboard.validate_storyboard(sb)
    matched = _issues(issues, "SFX_DURATION")

    assert matched, issues
    assert matched[0]["level"] == "error", matched[0]
    assert "deve" in (matched[0].get("msg") or "").lower(), matched[0]


@pytest.mark.parametrize("duration", [0.1, 0.5, 2.0])
def test_validate_sfx_finite_positive_duration_stays_valid(duration):
    from forja import storyboard

    sb = _sb(_padded_scene(_sfx(duration=duration)))
    issues = storyboard.validate_storyboard(sb)

    assert not _issues(issues, "SFX_DURATION"), issues
    assert not _errors(issues), issues


_TIMING_SPECS = [
    ({"hold_s": _NAN}, "hold_nan"),
    ({"hold_s": _INF}, "hold_inf"),
    ({"hold_s": _NINF}, "hold_menos_inf"),
    ({"enter": {"anchor": "at_s", "at_s": _NAN}}, "enter_at_s_nan"),
    ({"enter": {"anchor": "scene_start", "offset_s": _INF}}, "enter_offset_inf"),
    ({"exit": {"anchor": "at_s", "at_s": _NINF}}, "exit_at_s_menos_inf"),
    ({"exit": {"anchor": "scene_end", "offset_s": _NAN}}, "exit_offset_nan"),
]


@pytest.mark.parametrize("layer_type", ["sfx", "card"])
@pytest.mark.parametrize("spec, case_id", _TIMING_SPECS, ids=[s[1] for s in _TIMING_SPECS])
def test_validate_non_finite_layer_timing_is_layer_timing(layer_type, spec, case_id):
    from forja import storyboard

    if layer_type == "sfx":
        layer = _sfx(**spec)
    else:
        layer = {"type": "card", "asset": "assets/card.png", **spec}

    sb = _sb(_padded_scene(layer))
    issues = storyboard.validate_storyboard(sb)
    matched = _issues(issues, "LAYER_TIMING")

    assert matched, issues
    assert matched[0]["level"] == "error", matched[0]
    assert "deve" in (matched[0].get("msg") or "").lower(), matched[0]


def test_validate_finite_layer_timing_stays_valid():
    from forja import storyboard

    layer = _sfx(
        enter={"anchor": "at_s", "at_s": 0.5, "offset_s": 0.1},
        exit={"anchor": "scene_end", "offset_s": -0.1},
        hold_s=1.0,
    )
    sb = _sb(_padded_scene(layer))
    issues = storyboard.validate_storyboard(sb)

    assert not _issues(issues, "LAYER_TIMING"), issues
    assert not _issues(issues, "SFX_DURATION"), issues
    assert not _errors(issues), issues


# ------------------------------------- B1: id ausente e id vazio sao iguais


@pytest.mark.parametrize(
    "first, second",
    [
        (None, None),
        (None, ""),
        ("", None),
        ("", ""),
    ],
    ids=["ambos_ausentes", "ausente_e_vazio", "vazio_e_ausente", "ambos_vazios"],
)
def test_timeline_empty_scene_ids_are_duplicate(tmp_path, first, second):
    from forja import errors

    sb = _sb(
        _scene(first, {"fixed_s": 2.0}, []),
        _scene(second, {"fixed_s": 2.0}, []),
    )
    root = _new_storyboard_project(tmp_path, sb)

    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "CONFIG_INVALID"
    details = error.details or {}
    assert _empty_id_label(details.get("scene")), details
    hint = (error.hint or "").lower()
    assert hint
    assert any(token in hint for token in ("id", "duplic", "unic", "ún"))
    assert not (root / "work" / "timeline.json").exists()


# ------------------------------------------- B2: hint do enter fora da cena


def test_timeline_sfx_enter_at_s_outside_scene_hint_cites_value(tmp_path):
    from forja import errors

    sb = _sb(_padded_scene(_sfx(duration=0.5, enter={"anchor": "at_s", "at_s": 5.0})))
    root = _new_storyboard_project(tmp_path, sb)

    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "CONFIG_INVALID"
    details = error.details or {}
    assert details.get("scene") == "s1"
    assert float(details.get("start")) == pytest.approx(5.0)
    assert float(details.get("scene_start")) == pytest.approx(0.0)
    assert float(details.get("scene_end")) == pytest.approx(2.0)

    hint = (error.hint or "").lower()
    assert "5.0" in hint, hint
    assert "fora" in hint, hint
    assert "at_s" in hint or "offset_s" in hint, hint
    assert "no fim da cena" not in hint, hint
    assert not (root / "work" / "timeline.json").exists()


def test_timeline_sfx_enter_scene_start_offset_outside_scene_hint_cites_value(tmp_path):
    from forja import errors

    layer = _sfx(
        duration=0.5,
        enter={"anchor": "scene_start", "offset_s": 2.5},
    )
    sb = _sb(_padded_scene(layer))
    root = _new_storyboard_project(tmp_path, sb)

    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "CONFIG_INVALID"
    hint = (error.hint or "").lower()
    assert "2.5" in hint, hint
    assert "fora" in hint, hint
    assert "offset_s" in hint, hint
    assert "no fim da cena" not in hint, hint
    assert not (root / "work" / "timeline.json").exists()


def test_timeline_sfx_enter_word_outside_scene_hint_cites_value(monkeypatch, tmp_path):
    from forja import errors
    from forja.workflows import storyboard as workflow

    layer = _sfx(duration=0.5, enter={"anchor": "word", "word": "dois"})
    sb = _sb(_scene("s1", {"fixed_s": 2.0}, [_narration("um dois"), layer]))
    root = _new_storyboard_project(tmp_path, sb)
    _write_voice_cache(root, {"s1": 3.0})
    monkeypatch.setattr(
        workflow.transcribe,
        "run_transcribe",
        lambda *args, **kwargs: _fake_transcript([("um", 0.0), ("dois", 2.5)]),
    )

    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "CONFIG_INVALID"
    hint = (error.hint or "").lower()
    assert "2.5" in hint, hint
    assert "fora" in hint, hint
    assert "word" in hint or "palavra" in hint or "offset_s" in hint, hint
    assert "no fim da cena" not in hint, hint
    assert not (root / "work" / "timeline.json").exists()


def test_timeline_sfx_enter_scene_end_hint_keeps_end_of_scene(tmp_path):
    from forja import errors

    sb = _sb(_padded_scene(_sfx(duration=0.5, enter={"anchor": "scene_end"})))
    root = _new_storyboard_project(tmp_path, sb)

    with pytest.raises(errors.ForjaError) as excinfo:
        _step(root, "timeline").run(_make_ctx(root))

    error = excinfo.value
    assert error.code == "CONFIG_INVALID"
    hint = (error.hint or "").lower()
    assert "fim da cena" in hint, hint
    assert "offset_s" in hint, hint
    assert not (root / "work" / "timeline.json").exists()
