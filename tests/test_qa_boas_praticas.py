"""Contrato: legenda embutida obrigatoria e duracao editorial (videos oficiais)."""

def _ev(start=1.0, end=2.0):
    return {"start": start, "end": end, "lines": ["texto"]}


def test_captions_reels_none_missing():
    from forja import qa
    assert [(i["level"], i["id"], i["code"]) for i in qa.check_embedded_captions(None, "ig-reels")] == [("error", None, "CAPTIONS_MISSING")]


def test_captions_reels_empty_missing():
    from forja import qa
    assert [(i["level"], i["id"], i["code"]) for i in qa.check_embedded_captions([], "ig-reels")] == [("error", None, "CAPTIONS_MISSING")]


def test_captions_story_empty_missing():
    from forja import qa
    assert [(i["level"], i["id"], i["code"]) for i in qa.check_embedded_captions([], "ig-story")] == [("error", None, "CAPTIONS_MISSING")]


def test_captions_reels_with_event_ok():
    from forja import qa
    assert qa.check_embedded_captions([_ev()], "ig-reels") == []


def test_captions_feed_empty_ok():
    from forja import qa
    assert qa.check_embedded_captions([], "ig-feed-4x5") == []


def test_captions_yt_empty_ok():
    from forja import qa
    assert qa.check_embedded_captions([], "yt-16x9") == []


def test_duration_reels_at_target_ok():
    from forja import qa
    assert qa.check_editorial_duration("ig-reels", 60) == []


def test_duration_reels_over_target_warn():
    from forja import qa
    assert [(i["level"], i["id"], i["code"]) for i in qa.check_editorial_duration("ig-reels", 60.5)] == [("warn", None, "DURATION_TARGET")]


def test_duration_story_screens_ok():
    from forja import qa
    assert qa.check_editorial_duration("ig-story", 15, [15, 14.9]) == []


def test_duration_story_first_screen_long():
    from forja import qa
    assert [(i["level"], i["id"], i["code"]) for i in qa.check_editorial_duration("ig-story", 31, [16, 15])] == [("warn", 0, "STORY_SCREEN_LONG")]


def test_duration_story_two_screens_long():
    from forja import qa
    assert [(i["level"], i["id"], i["code"]) for i in qa.check_editorial_duration("ig-story", 32, [16, 16])] == [("warn", 0, "STORY_SCREEN_LONG"), ("warn", 1, "STORY_SCREEN_LONG")]


def test_duration_story_without_screens_ok():
    from forja import qa
    assert qa.check_editorial_duration("ig-story", 15) == []


def test_duration_other_format_ok():
    from forja import qa
    assert qa.check_editorial_duration("ig-feed-4x5", 120) == []


def test_duration_none_ok():
    from forja import qa
    assert qa.check_editorial_duration("ig-reels", None) == []


def test_duration_negative_ok():
    from forja import qa
    assert qa.check_editorial_duration("ig-reels", -1) == []
