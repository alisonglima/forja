"""Contract tests for forja.schedule (see DESIGN.md)."""
import numpy as np
import pytest


def _cfg(min_tempo=0.9, max_tempo=1.2):
    return {"voices": {"min_tempo": min_tempo, "max_tempo": max_tempo}}


def _cue(cid="A", t0=1.0, t1=3.0, lead=0.3, role="speech"):
    return {"id": cid, "t0": t0, "t1": t1, "lead": lead, "role": role, "text": "texto"}


def _codes(result):
    """Warning codes, accepting plain strings or ISSUE-like dicts."""
    out = set()
    for w in result.get("warnings", []):
        out.add(w if isinstance(w, str) else w.get("code"))
    for c in result.get("cues", []):
        for w in c.get("warnings", []):
            out.add(w if isinstance(w, str) else w.get("code"))
    return out


def test_speech_bounds_returns_none_for_total_silence():
    from forja import schedule
    assert schedule.speech_bounds(np.zeros(24000, dtype=np.float32), 24000) is None


def test_speech_bounds_returns_none_for_empty_samples():
    from forja import schedule
    assert schedule.speech_bounds(np.array([], dtype=np.float32), 24000) is None


def test_speech_bounds_detects_burst_bounds():
    from forja import schedule
    samples = np.zeros(24000, dtype=np.float32)
    samples[12000:13200] = 0.5
    start, end = schedule.speech_bounds(samples, 24000)
    assert 0.45 <= start < end <= 0.60, (start, end)


def test_speech_bounds_respects_threshold():
    from forja import schedule
    quiet = np.full(24000, 0.01, dtype=np.float32)
    assert schedule.speech_bounds(quiet, 24000) is None
    assert schedule.speech_bounds(quiet, 24000, thr=0.005) is not None


def test_speech_bounds_uses_absolute_amplitude():
    from forja import schedule
    samples = np.zeros(24000, dtype=np.float32)
    samples[12000:13200] = -0.5
    bounds = schedule.speech_bounds(samples, 24000)
    assert bounds is not None and bounds[0] < bounds[1], bounds


def test_plan_returns_contract_shape_for_speech_cue():
    from forja import schedule
    result = schedule.plan([_cue()], {"A": 0.1}, _cfg(), 10.0, {"A": (1.0, 3.0)})
    assert {"total", "cues", "warnings"} <= set(result)
    assert {"id", "start", "end", "tempo", "trim_start", "trim_end", "lag", "warnings"} <= set(result["cues"][0])


def test_plan_uses_bounds_speech_length():
    from forja import schedule
    result = schedule.plan([_cue()], {"A": 0.1}, _cfg(), 10.0, {"A": (1.0, 3.0)})
    cue = result["cues"][0]
    assert (cue["start"], cue["end"], cue["tempo"]) == pytest.approx((1.3, 3.0, 2.0 / 1.7))


def test_plan_falls_back_to_duration_when_bounds_is_none():
    from forja import schedule
    result = schedule.plan([_cue()], {"A": 2.0}, _cfg(), 10.0, {"A": None})
    assert result["cues"][0]["end"] == pytest.approx(3.0)


def test_plan_uses_bounds_over_duration():
    from forja import schedule
    result = schedule.plan([_cue()], {"A": 0.5}, _cfg(), 10.0, {"A": (1.0, 2.0)})
    assert result["cues"][0]["end"] == pytest.approx(1.3 + 1.0 / 0.9)


def test_plan_narrator_window_ends_at_next_cue_start():
    from forja import schedule
    cues = [_cue("A", 1.0, 1.5, role="narrator"), _cue("B", 4.0, 6.0)]
    result = schedule.plan(cues, {"A": 2.0, "B": 1.0}, _cfg(), 10.0, {"A": None, "B": None})
    assert result["cues"][0]["end"] == pytest.approx(1.3 + 2.0 / 0.9)


def test_plan_last_narrator_window_ends_at_total():
    from forja import schedule
    cues = [_cue("A", 1.0, 1.5, role="narrator")]
    result = schedule.plan(cues, {"A": 2.0}, _cfg(), 10.0, {"A": None})
    assert result["cues"][0]["end"] == pytest.approx(1.3 + 2.0 / 0.9)


def test_plan_clamps_tempo_to_config_max():
    from forja import schedule
    result = schedule.plan([_cue(t1=2.0)], {"A": 0.1}, _cfg(), 10.0, {"A": (1.0, 3.0)})
    cue = result["cues"][0]
    assert cue["tempo"] == pytest.approx(1.2) and "TEMPO_CLAMPED" in _codes(result)


def test_plan_clamps_tempo_to_config_min():
    from forja import schedule
    result = schedule.plan([_cue()], {"A": 0.1}, _cfg(), 10.0, {"A": (1.0, 1.2)})
    assert result["cues"][0]["tempo"] == pytest.approx(0.9)


def test_plan_never_exceeds_absolute_tempo_ceiling():
    from forja import schedule
    result = schedule.plan([_cue(t1=2.0)], {"A": 0.1}, _cfg(0.1, 5.0), 10.0, {"A": (1.0, 3.0)})
    assert result["cues"][0]["tempo"] == pytest.approx(2.0)


def test_plan_never_exceeds_absolute_tempo_floor():
    from forja import schedule
    result = schedule.plan([_cue()], {"A": 0.1}, _cfg(0.1, 5.0), 10.0, {"A": (1.0, 1.2)})
    assert result["cues"][0]["tempo"] == pytest.approx(0.5)


def test_plan_emits_overflow_when_lag_exceeds_quarter_second():
    from forja import schedule
    result = schedule.plan([_cue(t1=2.0)], {"A": 0.1}, _cfg(), 10.0, {"A": (1.0, 3.0)})
    assert result["cues"][0]["lag"] > 0.25 and "OVERFLOW" in _codes(result)


def test_plan_does_not_push_following_cue():
    from forja import schedule
    cues = [_cue("A", 1.0, 2.0), _cue("B", 4.0, 6.0)]
    result = schedule.plan(cues, {"A": 0.1, "B": 1.0}, _cfg(), 10.0, {"A": (1.0, 3.0), "B": None})
    assert [c["start"] for c in result["cues"]] == pytest.approx([1.3, 4.3])


def test_plan_sorts_cues_by_t0():
    from forja import schedule
    cues = [_cue("B", 5.0, 7.0), _cue("A", 1.0, 3.0)]
    result = schedule.plan(cues, {"A": 1.0, "B": 1.0}, _cfg(), 10.0, {"A": None, "B": None})
    assert [c["id"] for c in result["cues"]] == ["A", "B"]


def test_plan_keeps_lag_zero_when_speech_fits():
    from forja import schedule
    result = schedule.plan([_cue()], {"A": 0.1}, _cfg(), 10.0, {"A": (1.0, 1.5)})
    assert result["cues"][0]["lag"] == pytest.approx(0.0)


def test_plan_preserves_total():
    from forja import schedule
    result = schedule.plan([_cue()], {"A": 1.0}, _cfg(), 12.345, {"A": None})
    assert result["total"] == pytest.approx(12.345)
