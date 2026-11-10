"""Contract tests for forja.qa (see DESIGN.md)."""
import pytest


def _cfg(max_chars_line=42, max_lines=2, cps_max=20.0, fps=30,
         max_overlap_frames=2, target_lufs=-16.0, lufs_tol=1.0, max_true_peak=-1.0):
    return {
        "render": {"max_chars_line": max_chars_line, "max_lines": max_lines,
                   "cps_max": cps_max, "fps": fps},
        "qa": {"lufs_tol": lufs_tol, "max_true_peak": max_true_peak,
               "max_overlap_frames": max_overlap_frames},
        "mix": {"target_lufs": target_lufs},
    }


def _sub(start, end, lines=None, narrador=False, raised=False):
    return {"start": start, "end": end, "lines": lines or ["texto"],
            "narrador": narrador, "raised": raised}


def _sched_cue(cid="A", lag=0.0, warnings=None):
    return {"id": cid, "start": 1.0, "end": 2.0, "tempo": 1.0,
            "trim_start": 0.0, "trim_end": 0.0, "lag": lag,
            "warnings": list(warnings or [])}


def _schedule(*cues):
    warnings = [w for c in cues for w in c["warnings"]]
    return {"total": 10.0, "cues": list(cues), "warnings": warnings}


def _codes(issues):
    return [i.get("code") for i in issues]


def test_wer_is_zero_for_identical_text():
    from forja import qa
    assert qa.wer("the quick brown fox", "the quick brown fox") == pytest.approx(0.0)


def test_wer_ignores_case_and_punctuation():
    from forja import qa
    assert qa.wer("Hello, world!", "hello world") == pytest.approx(0.0)


def test_wer_counts_substitution_over_reference_length():
    from forja import qa
    assert qa.wer("the quick brown fox", "the quick brown cat") == pytest.approx(0.25)


def test_wer_counts_deletion_over_reference_length():
    from forja import qa
    assert qa.wer("a b c d", "a b c") == pytest.approx(0.25)


def test_wer_counts_insertion_over_reference_length():
    from forja import qa
    assert qa.wer("a b c", "a b c d") == pytest.approx(1.0 / 3.0)


def test_wer_is_one_for_empty_hypothesis():
    from forja import qa
    assert qa.wer("a b", "") == pytest.approx(1.0)


def test_check_subs_accepts_valid_event():
    from forja import qa
    assert qa.check_subs([_sub(1.0, 3.0, ["texto curto"])], _cfg()) == []


def test_check_subs_flags_cps_above_limit():
    from forja import qa
    issues = qa.check_subs([_sub(1.0, 2.0, ["x" * 30])], _cfg())
    assert "CPS" in _codes(issues) and {"level", "code", "msg"} <= set(issues[0])


def test_check_subs_flags_too_many_lines():
    from forja import qa
    issues = qa.check_subs([_sub(1.0, 2.0, ["a", "b", "c"])], _cfg())
    assert "LINES" in _codes(issues)


def test_check_subs_flags_line_longer_than_limit():
    from forja import qa
    issues = qa.check_subs([_sub(1.0, 2.0, ["x" * 43])], _cfg())
    assert "LINE_LONG" in _codes(issues)


def test_check_subs_flags_duration_below_minimum():
    from forja import qa
    issues = qa.check_subs([_sub(1.0, 1.5, ["ok"])], _cfg())
    assert "DURATION" in _codes(issues)


def test_check_subs_flags_overlapping_events():
    from forja import qa
    issues = qa.check_subs([_sub(1.0, 2.0), _sub(1.5, 3.0)], _cfg())
    assert "OVERLAP" in _codes(issues)


def test_check_subs_accepts_exact_boundaries():
    from forja import qa
    issues = qa.check_subs([_sub(1.0, 1.8, ["x" * 42, "y"])], _cfg(cps_max=100.0))
    assert issues == []


def test_check_overlap_flags_non_raised_event_over_tag():
    from forja import qa
    issues = qa.check_overlap([_sub(1.0, 2.0)], [[0.5, 1.5]], _cfg())
    assert any(i["level"] == "error" and i["code"] == "TAG_OVERLAP" for i in issues)


def test_check_overlap_ignores_raised_event():
    from forja import qa
    assert qa.check_overlap([_sub(1.0, 2.0, raised=True)], [[0.5, 1.5]], _cfg()) == []


def test_check_overlap_ignores_overlap_below_frame_budget():
    from forja import qa
    assert qa.check_overlap([_sub(1.0, 2.0)], [[2.03, 2.5]], _cfg()) == []


def test_check_overlap_flags_overlap_above_frame_budget():
    from forja import qa
    issues = qa.check_overlap([_sub(1.0, 2.0)], [[2.1, 2.5]], _cfg())
    assert "TAG_OVERLAP" in _codes(issues)


def test_check_overlap_ignores_event_outside_tag_window():
    from forja import qa
    assert qa.check_overlap([_sub(1.0, 2.0)], [[3.0, 4.0]], _cfg()) == []


def test_check_overlap_ignores_touching_boundary():
    from forja import qa
    assert qa.check_overlap([_sub(1.0, 2.0)], [[2.0, 2.5]], _cfg()) == []


def test_check_loudness_accepts_report_within_tolerance():
    from forja import qa
    assert qa.check_loudness({"I": -16.0, "TP": -2.0}, _cfg()) == []


def test_check_loudness_flags_lufs_out_of_tolerance():
    from forja import qa
    assert "LUFS" in _codes(qa.check_loudness({"I": -18.5, "TP": -2.0}, _cfg()))


def test_check_loudness_flags_true_peak_above_limit():
    from forja import qa
    assert "TRUE_PEAK" in _codes(qa.check_loudness({"I": -16.0, "TP": -0.5}, _cfg()))


def test_check_loudness_accepts_exact_tolerance_and_peak_boundaries():
    from forja import qa
    assert qa.check_loudness({"I": -15.0, "TP": -1.0}, _cfg()) == []


def test_check_loudness_flags_both_problems():
    from forja import qa
    codes = _codes(qa.check_loudness({"I": -20.0, "TP": 0.0}, _cfg()))
    assert "LUFS" in codes and "TRUE_PEAK" in codes


def test_check_schedule_accepts_clean_schedule():
    from forja import qa
    assert qa.check_schedule(_schedule(_sched_cue())) == []


def test_check_schedule_turns_tempo_clamped_into_warning():
    from forja import qa
    issues = qa.check_schedule(_schedule(_sched_cue(warnings=["TEMPO_CLAMPED"])))
    assert any(i["code"] == "TEMPO_CLAMPED" and i["level"] == "warn" for i in issues)


def test_check_schedule_turns_large_lag_into_error():
    from forja import qa
    issues = qa.check_schedule(_schedule(_sched_cue(lag=0.9, warnings=["OVERFLOW"])))
    assert any(i["level"] == "error" and i.get("id") == "A" for i in issues)
    assert any(i["code"] == "OVERFLOW" and i["level"] == "warn" for i in issues)


def test_check_schedule_accepts_lag_at_exact_threshold():
    from forja import qa
    assert qa.check_schedule(_schedule(_sched_cue(lag=0.6))) == []


def test_summarize_empty_issues_is_ok():
    from forja import qa
    assert qa.summarize([]) == {"ok": True, "errors": 0, "warnings": 0, "issues": []}


def test_summarize_counts_errors_and_warnings():
    from forja import qa
    issues = [{"level": "error", "code": "X"}, {"level": "warn", "code": "Y"},
              {"level": "warn", "code": "Z"}]
    summary = qa.summarize(issues)
    assert summary["ok"] is False and summary["errors"] == 1 and summary["warnings"] == 2


def test_summarize_warnings_only_is_ok_and_preserves_issues():
    from forja import qa
    issues = [{"level": "warn", "code": "Y"}]
    summary = qa.summarize(issues)
    assert summary["ok"] is True and summary["issues"] == issues
