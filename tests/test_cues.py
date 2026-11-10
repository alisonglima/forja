"""Contratos de forja.cues descritos no DESIGN.md."""
import json

import pytest

CFG = {
    "voices": {"min_tempo": 0.90, "max_tempo": 1.20},
    "render": {"max_chars_line": 42, "max_lines": 2, "cps_max": 20.0},
}


def _cue(**overrides):
    cue = {
        "id": "A",
        "speaker": "narradora",
        "role": "speech",
        "t0": 1.0,
        "t1": 4.0,
        "lead": 0.3,
        "text": "texto curto de teste",
    }
    cue.update(overrides)
    return cue


def _write_cues(tmp_path, data):
    path = tmp_path / "cues.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _codes(issues):
    return [issue["code"] for issue in issues]


def test_load_cues_fills_default_lead(tmp_path):
    from forja import cues

    path = _write_cues(
        tmp_path, [{"id": "A", "role": "speech", "t0": 0.0, "t1": 1.0, "text": "oi"}]
    )
    assert cues.load_cues(path)[0]["lead"] == pytest.approx(0.3)


def test_load_cues_fills_default_role_speech(tmp_path):
    from forja import cues

    path = _write_cues(
        tmp_path, [{"id": "A", "t0": 0.0, "t1": 1.0, "text": "oi"}]
    )
    assert cues.load_cues(path)[0]["role"] == "speech"


def test_load_cues_preserves_explicit_values(tmp_path):
    from forja import cues

    path = _write_cues(tmp_path, [_cue(lead=0.5, role="narrator")])
    loaded = cues.load_cues(path)[0]
    assert (loaded["lead"], loaded["role"]) == (0.5, "narrator")


def test_load_cues_preserves_order_and_extra_fields(tmp_path):
    from forja import cues

    path = _write_cues(
        tmp_path,
        [
            _cue(id="A", voice="Puck"),
            _cue(id="B", t0=5.0, t1=6.0, text="outro"),
        ],
    )
    loaded = cues.load_cues(path)
    assert [cue["id"] for cue in loaded] == ["A", "B"]
    assert loaded[0]["voice"] == "Puck"


def test_estimate_duration_uses_words_per_second():
    from forja import cues

    text = "one two three four five six seven"
    assert cues.estimate_duration_s(text) == pytest.approx(7 / 2.8)


def test_estimate_duration_of_empty_text_is_zero():
    from forja import cues

    assert cues.estimate_duration_s("") == 0.0


def test_estimate_duration_ignores_extra_whitespace():
    from forja import cues

    assert cues.estimate_duration_s("  um   dois \n tres ") == pytest.approx(3 / 2.8)


def test_split_lines_keeps_short_text_on_one_line():
    from forja import cues

    assert cues.split_lines("texto curto", 42, 2) == ["texto curto"]


def test_split_lines_preserves_every_word():
    from forja import cues

    text = "alpha beta gamma delta epsilon"
    lines = cues.split_lines(text, 12, 3)
    assert lines is not None and " ".join(lines) == text


def test_split_lines_respects_max_chars():
    from forja import cues

    lines = cues.split_lines("alpha beta gamma delta epsilon", 12, 3)
    assert lines is not None and all(len(line) <= 12 for line in lines)


def test_split_lines_returns_none_when_too_many_lines():
    from forja import cues

    text = "aaaa bbbb cccc dddd eeee"
    assert cues.split_lines(text, 10, 2) is None


def test_split_lines_returns_none_for_word_longer_than_max_chars():
    from forja import cues

    assert cues.split_lines("supercalifragilistic", 5, 3) is None


def test_split_lines_accepts_exact_fit():
    from forja import cues

    assert cues.split_lines("aa bb", 5, 1) == ["aa bb"]


def test_split_lines_breaks_after_punctuation():
    from forja import cues

    assert cues.split_lines("Hello, world", 6, 2) == ["Hello,", "world"]


def test_validate_cues_accepts_a_valid_cue():
    from forja import cues

    assert cues.validate_cues([_cue()], CFG) == []


def test_validate_cues_reports_missing_field():
    from forja import cues

    cue = _cue()
    del cue["text"]
    issues = cues.validate_cues([cue], CFG)
    assert any(
        issue["code"] == "MISSING_FIELD" and issue["level"] == "error"
        for issue in issues
    )


def test_validate_cues_reports_duplicate_id():
    from forja import cues

    issues = cues.validate_cues(
        [
            _cue(id="A", t0=1.0, t1=2.0, text="ok"),
            _cue(id="A", t0=3.0, t1=4.0, text="ok"),
        ],
        CFG,
    )
    assert any(
        issue["code"] == "DUP_ID" and issue["level"] == "error" for issue in issues
    )


def test_validate_cues_reports_time_order_when_t1_equals_t0():
    from forja import cues

    issues = cues.validate_cues([_cue(t1=1.0, text="ok")], CFG)
    assert any(
        issue["code"] == "T_ORDER" and issue["level"] == "error" for issue in issues
    )


def test_validate_cues_reports_lines_when_text_cannot_fit():
    from forja import cues

    cfg = {**CFG, "render": {**CFG["render"], "max_chars_line": 10, "max_lines": 1}}
    issues = cues.validate_cues([_cue(text="palavra enorme")], cfg)
    assert any(
        issue["code"] == "LINES" and issue["level"] == "error" for issue in issues
    )


def test_validate_cues_reports_cps_as_warning():
    from forja import cues

    issues = cues.validate_cues([_cue(t0=1.0, t1=2.0, text="a" * 30)], CFG)
    assert any(
        issue["code"] == "CPS" and issue["level"] == "warn" for issue in issues
    )


def test_validate_cues_does_not_warn_cps_at_exact_limit():
    from forja import cues

    issues = cues.validate_cues([_cue(t0=1.0, t1=2.0, text="a" * 20)], CFG)
    assert "CPS" not in _codes(issues)


def test_validate_cues_reports_budget_overflow():
    from forja import cues

    issues = cues.validate_cues([_cue(t0=1.0, t1=3.0, text="a a a a a a a")], CFG)
    assert any(
        issue["code"] == "BUDGET" and issue["level"] == "error" for issue in issues
    )


def test_validate_cues_accepts_text_within_budget():
    from forja import cues

    issues = cues.validate_cues([_cue(t0=1.0, t1=5.0, text="a a a a a a a")], CFG)
    assert "BUDGET" not in _codes(issues)


def test_validate_cues_reports_overlap_as_warning():
    from forja import cues

    issues = cues.validate_cues(
        [
            _cue(id="A", t0=1.0, t1=4.0, text="ok"),
            _cue(id="B", t0=3.0, t1=6.0, text="ok"),
        ],
        CFG,
    )
    assert any(
        issue["code"] == "OVERLAP" and issue["level"] == "warn" for issue in issues
    )


def test_validate_cues_issues_have_the_documented_shape():
    from forja import cues

    cue = _cue()
    del cue["text"]
    issues = cues.validate_cues([cue, _cue(id="A", t0=5.0, t1=6.0)], CFG)
    assert issues and all(
        {"level", "id", "code", "msg"} <= set(issue)
        and issue["level"] in {"error", "warn"}
        for issue in issues
    )


def test_issue_constant_has_documented_keys():
    from forja import cues

    assert set(cues.ISSUE) == {"level", "id", "code", "msg"}


def test_validate_cues_accepts_empty_list():
    from forja import cues

    assert cues.validate_cues([], CFG) == []


def test_load_cues_rejects_a_non_list_document(tmp_path):
    from forja import cues
    from forja.errors import ForjaError

    path = _write_cues(tmp_path, {"a": 1})
    with pytest.raises(ForjaError) as excinfo:
        cues.load_cues(path)
    assert excinfo.value.code == "CONFIG_INVALID"


def test_validate_cues_reports_unsafe_id():
    from forja import cues

    assert "BAD_ID" in _codes(cues.validate_cues([_cue(id="../PWNED")], CFG))
