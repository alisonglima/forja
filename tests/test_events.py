"""Contratos de forja.events descritos no DESIGN.md."""
import json
from datetime import datetime, timedelta

import pytest


def _lines(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _parse_utc(stamp):
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def test_emit_creates_work_dir_and_events_file(tmp_path):
    from forja import events

    work = tmp_path / "projeto" / "work"
    events.emit(work, "clip", "started")
    assert (work / "events.ndjson").is_file()


def test_emit_returns_the_appended_event(tmp_path):
    from forja import events

    event = events.emit(tmp_path, "clip", "started")
    assert event == _lines(tmp_path / "events.ndjson")[0]


def test_emit_timestamp_is_iso_8601_utc(tmp_path):
    from forja import events

    stamp = events.emit(tmp_path, "clip", "ok")["t"]
    assert stamp.endswith(("Z", "+00:00")) and _parse_utc(stamp).utcoffset() == timedelta(0)


def test_emit_appends_one_json_line_per_event(tmp_path):
    from forja import events

    events.emit(tmp_path, "clip", "started")
    events.emit(tmp_path, "clip", "ok")
    assert len(_lines(tmp_path / "events.ndjson")) == 2


def test_emit_keeps_extra_fields(tmp_path):
    from forja import events

    event = events.emit(tmp_path, "voices", "ok", cue="A", ms=12)
    assert (event["cue"], event["ms"]) == ("A", 12)


def test_emit_converts_path_values_to_string(tmp_path):
    from forja import events

    path = tmp_path / "voz.wav"
    event = events.emit(tmp_path, "voices", "ok", output=path)
    assert event["output"] == str(path) and isinstance(event["output"], str)


def test_emit_drops_sensitive_field_names(tmp_path):
    from forja import events

    event = events.emit(
        tmp_path,
        "tts",
        "started",
        api_key="a",
        token="b",
        secret="c",
        password="d",
        visible="e",
    )
    assert set(event) == {"t", "step", "status", "visible"}


@pytest.mark.parametrize("status", ["started", "ok", "skipped", "failed"])
def test_emit_accepts_each_documented_status(tmp_path, status):
    from forja import events

    assert events.emit(tmp_path, "passo", status)["status"] == status


def test_read_events_returns_last_limit_in_chronological_order(tmp_path):
    from forja import events

    for step in ("a", "b", "c", "d"):
        events.emit(tmp_path, step, "ok")
    assert [event["step"] for event in events.read_events(tmp_path, limit=2)] == [
        "c",
        "d",
    ]


def test_read_events_defaults_to_fifty_events(tmp_path):
    from forja import events

    for index in range(55):
        events.emit(tmp_path, "s%d" % index, "ok")
    read = events.read_events(tmp_path)
    assert (len(read), read[0]["step"], read[-1]["step"]) == (50, "s5", "s54")


def test_read_events_ignores_corrupted_lines(tmp_path):
    from forja import events

    path = tmp_path / "events.ndjson"
    path.write_text(
        '{"t": "2024-01-01T00:00:00Z", "step": "a", "status": "ok"}\n'
        "isto nao e json\n"
        "\n"
        '{"t": "2024-01-01T00:00:01Z", "step": "b", "status": "ok"}\n',
        encoding="utf-8",
    )
    assert [event["step"] for event in events.read_events(tmp_path)] == ["a", "b"]


def test_read_events_returns_empty_for_missing_work_dir(tmp_path):
    from forja import events

    assert events.read_events(tmp_path / "sem-work") == []
