"""Contratos de forja.storyboard descritos no DESIGN.md."""
import pytest

_UNSET = object()


def _narration(text="Hello world"):
    return {"type": "narration", "text": text, "lang": "en", "voice": "v1"}


def _captions():
    return {"type": "captions", "from": "narration"}


def _layer(layer_type, **fields):
    layer = {"type": layer_type}
    layer.update(fields)
    return layer


def _scene(scene_id="s1", layers=_UNSET, duration=_UNSET):
    return {
        "id": scene_id,
        "layers": [_narration(), _captions()] if layers is _UNSET else layers,
        "duration": {"fixed_s": 3.0} if duration is _UNSET else duration,
    }


def _sb(scenes=_UNSET, **overrides):
    storyboard = {
        "version": 1,
        "canvas": {"w": 1920, "h": 1080, "fps": 30},
        "scenes": [_scene()] if scenes is _UNSET else scenes,
    }
    storyboard.update(overrides)
    return storyboard


def _timeline_sb(*scenes):
    return {
        "version": 1,
        "canvas": {"w": 1280, "h": 720, "fps": 25},
        "scenes": list(scenes),
    }


def _codes(issues):
    return [issue["code"] for issue in issues]


def _has(issues, code, level="error"):
    return any(issue["code"] == code and issue["level"] == level for issue in issues)


# ---------------------------------------------------------------------------
# validate_storyboard
# ---------------------------------------------------------------------------


def test_validate_storyboard_accepts_minimal_valid_storyboard():
    from forja import storyboard

    assert storyboard.validate_storyboard(_sb()) == []


def test_validate_storyboard_reports_missing_version():
    from forja import storyboard

    sb = _sb()
    del sb["version"]
    assert _has(storyboard.validate_storyboard(sb), "SCHEMA")


def test_validate_storyboard_reports_version_other_than_one():
    from forja import storyboard

    assert _has(storyboard.validate_storyboard(_sb(version=2)), "SCHEMA")


def test_validate_storyboard_reports_missing_canvas():
    from forja import storyboard

    sb = _sb()
    del sb["canvas"]
    assert _has(storyboard.validate_storyboard(sb), "SCHEMA")


@pytest.mark.parametrize("key", ["w", "h", "fps"])
def test_validate_storyboard_requires_each_canvas_key(key):
    from forja import storyboard

    sb = _sb()
    del sb["canvas"][key]
    assert _has(storyboard.validate_storyboard(sb), "SCHEMA")


def test_validate_storyboard_reports_empty_scenes():
    from forja import storyboard

    assert _has(storyboard.validate_storyboard(_sb(scenes=[])), "SCHEMA")


def test_validate_storyboard_reports_scene_without_id():
    from forja import storyboard

    scene = _scene()
    del scene["id"]
    assert _has(storyboard.validate_storyboard(_sb(scenes=[scene])), "SCHEMA")


def test_validate_storyboard_reports_scene_without_layers():
    from forja import storyboard

    scene = _scene()
    del scene["layers"]
    assert _has(storyboard.validate_storyboard(_sb(scenes=[scene])), "SCHEMA")


def test_validate_storyboard_reports_layer_without_type():
    from forja import storyboard

    scene = _scene(layers=[{"text": "sem tipo"}])
    assert _has(storyboard.validate_storyboard(_sb(scenes=[scene])), "SCHEMA")


def test_validate_storyboard_reports_unknown_layer_type():
    from forja import storyboard

    scene = _scene(layers=[_layer("video")])
    assert _has(storyboard.validate_storyboard(_sb(scenes=[scene])), "SCHEMA")


def test_validate_storyboard_reports_duplicate_scene_id():
    from forja import storyboard

    sb = _sb(scenes=[_scene("a"), _scene("a")])
    assert _has(storyboard.validate_storyboard(sb), "DUP_SCENE")


def test_validate_storyboard_reports_missing_duration():
    from forja import storyboard

    scene = _scene()
    del scene["duration"]
    assert _has(storyboard.validate_storyboard(_sb(scenes=[scene])), "NO_DURATION")


@pytest.mark.parametrize("duration", [{}, {"from": "fixed"}])
def test_validate_storyboard_reports_invalid_duration(duration):
    from forja import storyboard

    scene = _scene(duration=duration)
    assert _has(storyboard.validate_storyboard(_sb(scenes=[scene])), "NO_DURATION")


def test_validate_storyboard_reports_from_narration_without_narration_layer():
    from forja import storyboard

    scene = _scene(layers=[_captions()], duration={"from": "narration"})
    assert _has(storyboard.validate_storyboard(_sb(scenes=[scene])), "NO_DURATION")


def test_validate_storyboard_accepts_from_narration_with_narration_layer():
    from forja import storyboard

    scene = _scene(duration={"from": "narration"})
    assert "NO_DURATION" not in _codes(storyboard.validate_storyboard(_sb(scenes=[scene])))


def test_validate_storyboard_ignores_assets_without_root():
    from forja import storyboard

    layers = [
        _layer("clip", source="file", file="nope.mp4", fit="cover"),
        _layer("card", asset="nope.png"),
        _layer("music", track="nope.mp3", license={"kind": "cc0"}),
    ]
    assert "ASSET_MISSING" not in _codes(
        storyboard.validate_storyboard(_sb(scenes=[_scene(layers=layers)]))
    )


def test_validate_storyboard_reports_missing_clip_file(tmp_path):
    from forja import storyboard

    layer = _layer("clip", source="file", file="nope.mp4", fit="cover")
    issues = storyboard.validate_storyboard(
        _sb(scenes=[_scene(layers=[layer])]), tmp_path
    )
    assert _has(issues, "ASSET_MISSING")


def test_validate_storyboard_reports_missing_card_asset(tmp_path):
    from forja import storyboard

    layer = _layer("card", asset="nope.png")
    issues = storyboard.validate_storyboard(
        _sb(scenes=[_scene(layers=[layer])]), tmp_path
    )
    assert _has(issues, "ASSET_MISSING")


def test_validate_storyboard_reports_missing_music_track(tmp_path):
    from forja import storyboard

    layer = _layer("music", track="nope.mp3", license={"kind": "cc0"})
    issues = storyboard.validate_storyboard(
        _sb(scenes=[_scene(layers=[layer])]), tmp_path
    )
    assert _has(issues, "ASSET_MISSING")


def test_validate_storyboard_accepts_existing_assets(tmp_path):
    from forja import storyboard

    for name in ("clip.mp4", "card.png", "music.mp3"):
        (tmp_path / name).write_bytes(b"x")
    layers = [
        _layer("clip", source="file", file="clip.mp4", fit="cover"),
        _layer("card", asset="card.png"),
        _layer("music", track="music.mp3", license={"kind": "cc0"}),
    ]
    issues = storyboard.validate_storyboard(
        _sb(scenes=[_scene(layers=layers)]), tmp_path
    )
    assert "ASSET_MISSING" not in _codes(issues)


def test_validate_storyboard_reports_music_without_license():
    from forja import storyboard

    layer = _layer("music", track="music.mp3", gain_db=-6.0, ducking=True)
    issues = storyboard.validate_storyboard(_sb(scenes=[_scene(layers=[layer])]))
    assert _has(issues, "MUSIC_NO_LICENSE")


def test_validate_storyboard_accepts_music_with_license_kind():
    from forja import storyboard

    layer = _layer("music", track="music.mp3", license={"kind": "licensed"})
    issues = storyboard.validate_storyboard(_sb(scenes=[_scene(layers=[layer])]))
    assert "MUSIC_NO_LICENSE" not in _codes(issues)


def test_validate_storyboard_warns_unresolved_word_anchor():
    from forja import storyboard

    card = _layer(
        "card",
        asset="card.png",
        enter={"anchor": "word", "word": "banana", "offset_s": 0.0},
    )
    scene = _scene(layers=[_narration("Hello world"), card])
    issues = storyboard.validate_storyboard(_sb(scenes=[scene]))
    assert _has(issues, "ANCHOR_UNRESOLVED", level="warn")


def test_validate_storyboard_accepts_resolved_word_anchor():
    from forja import storyboard

    card = _layer(
        "card",
        asset="card.png",
        enter={"anchor": "word", "word": "Hello", "offset_s": 0.0},
    )
    scene = _scene(layers=[_narration("Hello world"), card])
    issues = storyboard.validate_storyboard(_sb(scenes=[scene]))
    assert "ANCHOR_UNRESOLVED" not in _codes(issues)


def test_validate_storyboard_warns_unresolved_exit_anchor():
    from forja import storyboard

    card = _layer(
        "card",
        asset="card.png",
        exit={"anchor": "word", "word": "missing", "offset_s": 0.0},
    )
    scene = _scene(layers=[_narration("Hello world"), card])
    issues = storyboard.validate_storyboard(_sb(scenes=[scene]))
    assert _has(issues, "ANCHOR_UNRESOLVED", level="warn")


def test_validate_storyboard_reports_invalid_fit():
    from forja import storyboard

    layer = _layer("clip", source="file", file="clip.mp4", fit="stretch")
    issues = storyboard.validate_storyboard(_sb(scenes=[_scene(layers=[layer])]))
    assert _has(issues, "FIT")


def test_validate_storyboard_accepts_contain_fit():
    from forja import storyboard

    layer = _layer("clip", source="file", file="clip.mp4", fit="contain")
    issues = storyboard.validate_storyboard(_sb(scenes=[_scene(layers=[layer])]))
    assert "FIT" not in _codes(issues)


def test_validate_storyboard_issues_have_documented_shape():
    from forja import storyboard

    scene = _scene()
    del scene["duration"]
    issues = storyboard.validate_storyboard(_sb(scenes=[scene]))
    assert issues and all(
        {"level", "id", "code", "msg"} <= set(issue)
        and issue["level"] in {"error", "warn"}
        for issue in issues
    )


def test_validate_storyboard_issue_id_is_the_scene_id():
    from forja import storyboard

    scene = _scene("cena-1")
    del scene["duration"]
    issues = storyboard.validate_storyboard(_sb(scenes=[scene]))
    issue = next(issue for issue in issues if issue["code"] == "NO_DURATION")
    assert issue["id"] == "cena-1"


# ---------------------------------------------------------------------------
# resolve_timeline
# ---------------------------------------------------------------------------


def test_resolve_timeline_uses_fixed_scene_duration():
    from forja import storyboard

    tl = storyboard.resolve_timeline(
        _timeline_sb(_scene("a", duration={"fixed_s": 3.0})), {}
    )
    assert [tl["total_s"], tl["scenes"][0]["start"], tl["scenes"][0]["end"]] == (
        pytest.approx([3.0, 0.0, 3.0])
    )


def test_resolve_timeline_accumulates_scene_starts():
    from forja import storyboard

    tl = storyboard.resolve_timeline(
        _timeline_sb(
            _scene("a", duration={"fixed_s": 2.0}),
            _scene("b", duration={"fixed_s": 3.0}),
        ),
        {},
    )
    flat = [tl["total_s"]]
    for scene in tl["scenes"]:
        flat.extend([scene["start"], scene["end"]])
    assert flat == pytest.approx([5.0, 0.0, 2.0, 2.0, 5.0])


def test_resolve_timeline_uses_narration_with_pads():
    from forja import storyboard

    scene = _scene(
        "a", duration={"from": "narration", "pad_before": 0.5, "pad_after": 0.25}
    )
    tl = storyboard.resolve_timeline(_timeline_sb(scene), {"a": 2.0})
    assert tl["total_s"] == pytest.approx(2.75)


def test_resolve_timeline_defaults_pads_to_zero():
    from forja import storyboard

    scene = _scene("a", duration={"from": "narration"})
    tl = storyboard.resolve_timeline(_timeline_sb(scene), {"a": 2.0})
    assert tl["total_s"] == pytest.approx(2.0)


def test_resolve_timeline_reports_canvas_fps():
    from forja import storyboard

    tl = storyboard.resolve_timeline(_timeline_sb(_scene("a")), {})
    assert tl["fps"] == 25


def test_resolve_timeline_copies_layer_fields():
    from forja import storyboard

    tl = storyboard.resolve_timeline(_timeline_sb(_scene("a")), {})
    layer = next(item for item in tl["scenes"][0]["layers"] if item["type"] == "narration")
    expected = {"type": "narration", "text": "Hello world", "lang": "en", "voice": "v1"}
    assert all(layer.get(key) == value for key, value in expected.items())


def test_resolve_timeline_layer_spans_whole_scene_by_default():
    from forja import storyboard

    tl = storyboard.resolve_timeline(
        _timeline_sb(_scene("a", duration={"fixed_s": 3.0})), {}
    )
    captions = next(
        item for item in tl["scenes"][0]["layers"] if item["type"] == "captions"
    )
    assert [captions["start"], captions["end"]] == pytest.approx([0.0, 3.0])


def test_resolve_timeline_uses_enter_at_s_and_hold_s():
    from forja import storyboard

    card = _layer("card", asset="c.png", enter={"at_s": 0.5}, hold_s=1.0)
    tl = storyboard.resolve_timeline(
        _timeline_sb(_scene("a", layers=[card], duration={"fixed_s": 3.0})), {}
    )
    layer = tl["scenes"][0]["layers"][0]
    assert [layer["start"], layer["end"]] == pytest.approx([0.5, 1.5])


def test_resolve_timeline_enter_at_s_without_hold_ends_at_scene_end():
    from forja import storyboard

    card = _layer("card", asset="c.png", enter={"at_s": 0.5})
    tl = storyboard.resolve_timeline(
        _timeline_sb(_scene("a", layers=[card], duration={"fixed_s": 3.0})), {}
    )
    layer = tl["scenes"][0]["layers"][0]
    assert [layer["start"], layer["end"]] == pytest.approx([0.5, 3.0])


def test_resolve_timeline_word_anchor_adds_offset_and_pad_before():
    from forja import storyboard

    card = _layer(
        "card",
        asset="c.png",
        enter={"anchor": "word", "word": "Hello", "offset_s": 0.1},
        hold_s=0.5,
    )
    scene = _scene(
        "a",
        layers=[_narration("Hello world"), card],
        duration={"from": "narration", "pad_before": 0.5, "pad_after": 0.0},
    )
    words = {"a": [{"word": "Hello", "start": 0.2, "end": 0.5}]}
    tl = storyboard.resolve_timeline(_timeline_sb(scene), {"a": 2.0}, words)
    layer = next(item for item in tl["scenes"][0]["layers"] if item["type"] == "card")
    assert [layer["start"], layer["end"]] == pytest.approx([0.8, 1.3])


def test_resolve_timeline_word_anchor_ignores_case_and_punctuation():
    from forja import storyboard

    card = _layer(
        "card", asset="c.png", enter={"anchor": "word", "word": "Hello", "offset_s": 0.0}
    )
    scene = _scene("a", layers=[_narration("Hello world"), card], duration={"fixed_s": 2.0})
    words = {"a": [{"word": "hello,", "start": 0.4, "end": 0.6}]}
    tl = storyboard.resolve_timeline(_timeline_sb(scene), {}, words)
    layer = next(item for item in tl["scenes"][0]["layers"] if item["type"] == "card")
    assert layer["start"] == pytest.approx(0.4)


def test_resolve_timeline_unresolved_word_anchor_falls_back_to_scene_start():
    from forja import storyboard

    card = _layer(
        "card", asset="c.png", enter={"anchor": "word", "word": "banana", "offset_s": 0.0}
    )
    scene = _scene("a", layers=[_narration("Hello world"), card], duration={"fixed_s": 2.0})
    words = {"a": [{"word": "Hello", "start": 0.2, "end": 0.5}]}
    tl = storyboard.resolve_timeline(_timeline_sb(scene), {}, words)
    layer = next(item for item in tl["scenes"][0]["layers"] if item["type"] == "card")
    assert (layer["start"], bool(layer.get("warnings"))) == (0.0, True)


def test_resolve_timeline_word_anchor_without_words_falls_back_to_scene_start():
    from forja import storyboard

    card = _layer(
        "card", asset="c.png", enter={"anchor": "word", "word": "Hello", "offset_s": 0.0}
    )
    scene = _scene("a", layers=[_narration("Hello world"), card], duration={"fixed_s": 2.0})
    tl = storyboard.resolve_timeline(_timeline_sb(scene), {})
    layer = next(item for item in tl["scenes"][0]["layers"] if item["type"] == "card")
    assert layer["start"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# to_srt
# ---------------------------------------------------------------------------


def _timeline(*scenes):
    return {"fps": 30, "total_s": 10.0, "scenes": list(scenes)}


def _tl_scene(scene_id, start, end, layers):
    return {"id": scene_id, "start": start, "end": end, "layers": layers}


def _caption_layer(start, end):
    return {"type": "captions", "start": start, "end": end}


def test_to_srt_formats_timestamp_with_milliseconds():
    from forja import storyboard

    timeline = _timeline(_tl_scene("a", 0.0, 10.0, [_caption_layer(1.5, 3.0)]))
    out = storyboard.to_srt(timeline, {"a": ["Hello"]})
    assert "00:00:01,500 --> 00:00:03,000" in out


def test_to_srt_numbers_blocks_from_one():
    from forja import storyboard

    timeline = _timeline(_tl_scene("a", 0.0, 10.0, [_caption_layer(1.5, 3.0)]))
    out = storyboard.to_srt(timeline, {"a": ["Hello"]})
    assert out.startswith("1\n")


def test_to_srt_joins_text_lines():
    from forja import storyboard

    timeline = _timeline(_tl_scene("a", 0.0, 10.0, [_caption_layer(1.5, 3.0)]))
    out = storyboard.to_srt(timeline, {"a": ["Hello", "world"]})
    assert "Hello\nworld" in out


def test_to_srt_formats_hours():
    from forja import storyboard

    timeline = _timeline(_tl_scene("a", 0.0, 4000.0, [_caption_layer(3661.5, 3662.0)]))
    out = storyboard.to_srt(timeline, {"a": ["Late"]})
    assert "01:01:01,500 --> 01:01:02,000" in out


def test_to_srt_emits_one_block_per_captions_scene():
    from forja import storyboard

    timeline = _timeline(
        _tl_scene("a", 0.0, 2.0, [_caption_layer(0.0, 2.0)]),
        _tl_scene("b", 2.0, 4.0, [_caption_layer(2.0, 4.0)]),
    )
    out = storyboard.to_srt(timeline, {"a": ["One"], "b": ["Two"]})
    assert out.count("-->") == 2


def test_to_srt_skips_scenes_without_captions():
    from forja import storyboard

    timeline = _timeline(
        _tl_scene("a", 0.0, 2.0, [_caption_layer(0.0, 2.0)]),
        _tl_scene("b", 2.0, 4.0, [{"type": "narration", "start": 2.0, "end": 4.0}]),
    )
    out = storyboard.to_srt(timeline, {"a": ["One"], "b": ["Second"]})
    assert out.count("-->") == 1 and "Second" not in out


def test_to_srt_uses_captions_layer_bounds():
    from forja import storyboard

    timeline = _timeline(_tl_scene("a", 0.0, 10.0, [_caption_layer(2.0, 4.0)]))
    out = storyboard.to_srt(timeline, {"a": ["Hello"]})
    assert "00:00:02,000 --> 00:00:04,000" in out


def test_to_srt_uses_texts_keyed_by_scene_id():
    from forja import storyboard

    timeline = _timeline(
        _tl_scene("a", 0.0, 2.0, [_caption_layer(0.0, 2.0)]),
        _tl_scene("b", 2.0, 4.0, [_caption_layer(2.0, 4.0)]),
    )
    out = storyboard.to_srt(timeline, {"a": ["First"], "b": ["Second"]})
    assert out.index("First") < out.index("Second")


def test_to_srt_returns_empty_string_without_captions():
    from forja import storyboard

    assert storyboard.to_srt(_timeline(), {}) == ""


def _sb_speech_window(extra_layer=None):
    layers = [
        {"type": "narration", "text": "ola mundo"},
        {"type": "captions", "from": "narration"},
    ]
    if extra_layer:
        layers.append(extra_layer)
    return {
        "version": 1,
        "canvas": {"w": 1280, "h": 720, "fps": 30},
        "scenes": [
            {
                "id": "S1",
                "duration": {"from": "narration", "pad_before": 0.4, "pad_after": 0.5},
                "layers": layers,
            }
        ],
    }


def _speech_layer(timeline, kind):
    return next(l for l in timeline["scenes"][0]["layers"] if l["type"] == kind)


def test_captions_follow_the_narration_window_not_the_scene_padding():
    from forja import storyboard

    timeline = storyboard.resolve_timeline(_sb_speech_window(), {"S1": 2.0})
    captions = _speech_layer(timeline, "captions")
    assert (captions["start"], captions["end"]) == (0.4, 2.4)


def test_narration_layer_also_uses_the_speech_window():
    from forja import storyboard

    timeline = storyboard.resolve_timeline(_sb_speech_window(), {"S1": 2.0})
    narration = _speech_layer(timeline, "narration")
    assert (narration["start"], narration["end"]) == (0.4, 2.4)


def test_scene_still_includes_both_paddings():
    from forja import storyboard

    timeline = storyboard.resolve_timeline(_sb_speech_window(), {"S1": 2.0})
    assert (timeline["scenes"][0]["start"], timeline["scenes"][0]["end"]) == (0.0, 2.9)


def test_non_speech_layers_keep_the_whole_scene():
    from forja import storyboard

    clip = {"type": "clip", "file": "assets/c.mp4"}
    timeline = storyboard.resolve_timeline(_sb_speech_window(clip), {"S1": 2.0})
    layer = _speech_layer(timeline, "clip")
    assert (layer["start"], layer["end"]) == (0.0, 2.9)


def test_explicit_hold_on_captions_is_not_overridden():
    from forja import storyboard

    sb = _sb_speech_window()
    sb["scenes"][0]["layers"][1]["hold_s"] = 1.0
    timeline = storyboard.resolve_timeline(sb, {"S1": 2.0})
    captions = _speech_layer(timeline, "captions")
    assert (captions["start"], captions["end"]) == (0.0, 1.0)


def test_srt_uses_the_narration_window():
    from forja import storyboard

    timeline = storyboard.resolve_timeline(_sb_speech_window(), {"S1": 2.0})
    srt = storyboard.to_srt(timeline, {"S1": ["ola mundo"]})
    assert "00:00:00,400 --> 00:00:02,400" in srt


def test_validate_storyboard_rejects_assets_outside_the_project(tmp_path):
    """Asset nao pode sair da raiz do projeto (path traversal / caminho absoluto)."""
    from forja import storyboard

    outside = tmp_path.parent / (tmp_path.name + "-fora.mp4")
    outside.write_bytes(b"x")
    for value in ("../" + outside.name, str(outside)):
        layer = _layer("clip", source="file", file=value, fit="cover")
        issues = storyboard.validate_storyboard(
            _sb(scenes=[_scene(layers=[layer])]), tmp_path
        )
        assert _has(issues, "ASSET_OUTSIDE"), value


def test_validate_storyboard_reports_unsafe_scene_id():
    from forja import storyboard

    issues = storyboard.validate_storyboard(_sb(scenes=[_scene(scene_id="../PWNED")]))
    assert _has(issues, "BAD_ID")


def test_validate_storyboard_accepts_a_lower_third_overlay():
    from forja import storyboard

    sb = _sb(scenes=[_scene(layers=[
        _narration(),
        _captions(),
        {"type": "overlay", "preset": "lower_third", "text": "Ana", "subtext": "Diretora"},
    ])])
    assert storyboard.validate_storyboard(sb) == []


def test_validate_storyboard_rejects_unknown_overlay_preset():
    from forja import storyboard

    sb = _sb(scenes=[_scene(layers=[
        _narration(),
        {"type": "overlay", "preset": "hologram", "text": "x"},
    ])])
    assert _has(storyboard.validate_storyboard(sb), "OVERLAY_PRESET")


def test_validate_storyboard_requires_logo_asset():
    from forja import storyboard

    sb = _sb(scenes=[_scene(layers=[
        _narration(),
        {"type": "overlay", "preset": "logo"},
    ])])
    assert _has(storyboard.validate_storyboard(sb), "OVERLAY_ASSET")


def test_validate_storyboard_rejects_bad_overlay_style():
    from forja import storyboard

    sb = _sb(scenes=[_scene(layers=[
        _narration(),
        {"type": "overlay", "preset": "title", "text": "x", "style": {"opacity": 2}},
    ])])
    assert _has(storyboard.validate_storyboard(sb), "OVERLAY_STYLE")


def test_resolve_timeline_clips_overlay_at_scene_end():
    from forja import storyboard

    sb = _timeline_sb(
        {
            "id": "s1",
            "duration": {"fixed_s": 3.0},
            "layers": [
                {"type": "overlay", "preset": "title", "text": "x", "hold_s": 10},
            ],
        }
    )
    timeline = storyboard.resolve_timeline(sb, {})
    layer = timeline["scenes"][0]["layers"][0]
    assert layer["end"] == pytest.approx(3.0)
    assert "overlay cortado" in layer["warnings"][0]


def test_caption_windows_uses_default_position_for_lower_third():
    from forja import storyboard

    timeline = {
        "scenes": [
            {
                "id": "s1",
                "start": 0.0,
                "end": 4.0,
                "layers": [
                    {"type": "overlay", "preset": "lower_third", "text": "x", "start": 0.6, "end": 3.4}
                ],
            }
        ]
    }
    assert storyboard.caption_windows(timeline) == [[0.6, 3.4]]
