"""Contract tests for forja.subs (see DESIGN.md)."""
import pytest


def _cfg(max_chars_line=42, max_lines=2):
    return {"render": {"max_chars_line": max_chars_line, "max_lines": max_lines,
                       "cps_max": 20.0, "fps": 30}}


def _entry(cid, start, end):
    return {"id": cid, "start": start, "end": end, "tempo": 1.0,
            "trim_start": 0.0, "trim_end": 0.0, "lag": 0.0, "warnings": []}


def _cue(cid, text, role="speech", t0=0.0, t1=1.0):
    return {"id": cid, "text": text, "role": role, "t0": t0, "t1": t1, "lead": 0.3}


def _schedule(*entries):
    return {"total": entries[-1]["end"] if entries else 0.0,
            "cues": list(entries), "warnings": []}


def _sub(start, end, lines=None, narrador=False, raised=False):
    return {"start": start, "end": end, "lines": lines or ["texto"],
            "narrador": narrador, "raised": raised}


def test_build_subs_emits_one_event_for_short_text():
    from forja import subs
    schedule = _schedule(_entry("A", 0.5, 2.5))
    events = subs.build_subs(schedule, [_cue("A", "Olá mundo.", t0=0.5, t1=2.5)], [], _cfg())
    assert len(events) == 1 and " ".join(events[0]["lines"]) == "Olá mundo."


def test_build_subs_event_has_contract_keys():
    from forja import subs
    schedule = _schedule(_entry("A", 0.5, 2.5))
    event = subs.build_subs(schedule, [_cue("A", "texto curto", t0=0.5, t1=2.5)], [], _cfg())[0]
    assert {"start", "end", "lines", "narrador", "raised"} <= set(event)


def test_build_subs_marks_narrator_role():
    from forja import subs
    schedule = _schedule(_entry("A", 0.5, 2.5))
    event = subs.build_subs(schedule, [_cue("A", "narração", role="narrator", t0=0.5, t1=2.5)], [], _cfg())[0]
    assert event["narrador"] is True


def test_build_subs_raises_event_inside_lower_third():
    from forja import subs
    schedule = _schedule(_entry("A", 0.5, 2.5))
    event = subs.build_subs(schedule, [_cue("A", "texto", t0=0.5, t1=2.5)], [[1.0, 2.0]], _cfg())[0]
    assert event["raised"] is True


def test_build_subs_applies_lower_third_margin():
    from forja import subs
    schedule = _schedule(_entry("A", 0.5, 1.0))
    event = subs.build_subs(schedule, [_cue("A", "texto", t0=0.5, t1=1.0)], [[1.15, 1.5]], _cfg())[0]
    assert event["raised"] is True


def test_build_subs_does_not_raise_far_from_lower_third():
    from forja import subs
    schedule = _schedule(_entry("A", 0.5, 1.0))
    event = subs.build_subs(schedule, [_cue("A", "texto", t0=0.5, t1=1.0)], [[1.5, 2.0]], _cfg())[0]
    assert event["raised"] is False


def test_build_subs_splits_text_over_capacity():
    from forja import subs
    text = "alpha beta gamma delta"
    schedule = _schedule(_entry("A", 1.0, 5.0))
    events = subs.build_subs(schedule, [_cue("A", text, t0=1.0, t1=5.0)], [], _cfg(10, 1))
    words = " ".join(" ".join(e["lines"]) for e in events).split()
    assert len(events) >= 2 and words == text.split()


def test_build_subs_split_lines_fit_limits():
    from forja import subs
    schedule = _schedule(_entry("A", 1.0, 5.0))
    events = subs.build_subs(schedule, [_cue("A", "alpha beta gamma delta", t0=1.0, t1=5.0)], [], _cfg(10, 1))
    assert all(len(line) <= 10 for e in events for line in e["lines"]) and all(len(e["lines"]) <= 1 for e in events)


def test_build_subs_never_overlaps_events():
    from forja import subs
    schedule = _schedule(_entry("A", 1.0, 3.0), _entry("B", 2.5, 4.0))
    cues = [_cue("A", "primeiro", t0=1.0, t1=3.0), _cue("B", "segundo", t0=2.5, t1=4.0)]
    events = subs.build_subs(schedule, cues, [], _cfg())
    assert events[0]["end"] <= events[1]["start"] + 1e-9


def test_build_subs_enforces_minimum_duration_when_space():
    from forja import subs
    schedule = _schedule(_entry("A", 1.0, 1.2), _entry("B", 5.0, 6.0))
    cues = [_cue("A", "ok", t0=1.0, t1=1.2), _cue("B", "próximo", t0=5.0, t1=6.0)]
    events = subs.build_subs(schedule, cues, [], _cfg())
    assert events[0]["end"] - events[0]["start"] >= 0.8 - 1e-9


def test_build_subs_does_not_extend_into_next_event():
    from forja import subs
    schedule = _schedule(_entry("A", 1.0, 1.2), _entry("B", 1.3, 2.0))
    cues = [_cue("A", "ok", t0=1.0, t1=1.2), _cue("B", "próximo", t0=1.3, t1=2.0)]
    events = subs.build_subs(schedule, cues, [], _cfg())
    assert events[0]["end"] <= events[1]["start"] + 1e-9


def test_build_subs_returns_empty_for_no_cues():
    from forja import subs
    assert subs.build_subs(_schedule(), [], [], _cfg()) == []


def test_to_srt_formats_timecode_and_lines():
    from forja import subs
    srt = subs.to_srt([_sub(1.5, 3.0, ["Olá", "mundo"])])
    assert srt.startswith("1\n00:00:01,500 --> 00:00:03,000\nOlá\nmundo")


def test_to_srt_numbers_events_from_one():
    from forja import subs
    srt = subs.to_srt([_sub(1.0, 2.0), _sub(3.0, 4.0)])
    assert srt.count("-->") == 2 and "\n2\n" in srt


def test_to_srt_handles_hours():
    from forja import subs
    srt = subs.to_srt([_sub(3661.234, 3662.0)])
    assert "01:01:01,234 --> 01:01:02,000" in srt
