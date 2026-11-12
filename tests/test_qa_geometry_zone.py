"""Contrato `forja.qa_geometry.check_safe_zone` (T-GATEFIX-GEOM-01): zona assimétrica em frações com ceil, encostar passa, GATE_FAILED; `check_safe_area` intacto."""
from __future__ import annotations
import pytest
STORY_SIZE = (1080, 1920)
STORY_ZONE = {"top": 0.15, "bottom": 0.15, "left": 0.10, "right": 0.10}
FEED_SIZE = (1080, 1350)
FEED_ZONE = {"top": 0.05, "bottom": 0.05, "left": 0.05, "right": 0.05}
def _box(bid, x, y, w, h):
    return {"id": bid, "x": x, "y": y, "w": w, "h": h}
def test_exact_story_zone_passes():
    from forja import qa_geometry
    assert qa_geometry.check_safe_zone([_box("a", 108, 288, 864, 1344)], STORY_SIZE, STORY_ZONE) == []
def test_story_left_breach_fails():
    from forja import qa_geometry
    (issue,) = qa_geometry.check_safe_zone([_box("a", 107, 288, 864, 1344)], STORY_SIZE, STORY_ZONE)
    assert (issue["level"], issue["code"], issue["id"]) == ("error", "GATE_FAILED", "a") and issue["msg"]
def test_story_top_breach_fails():
    from forja import qa_geometry
    (issue,) = qa_geometry.check_safe_zone([_box("a", 108, 287, 864, 1344)], STORY_SIZE, STORY_ZONE)
    assert (issue["level"], issue["code"], issue["id"]) == ("error", "GATE_FAILED", "a") and issue["msg"]
def test_story_right_breach_fails():
    from forja import qa_geometry
    (issue,) = qa_geometry.check_safe_zone([_box("a", 109, 288, 864, 1344)], STORY_SIZE, STORY_ZONE)
    assert (issue["level"], issue["code"], issue["id"]) == ("error", "GATE_FAILED", "a") and issue["msg"]
def test_story_bottom_breach_fails():
    from forja import qa_geometry
    (issue,) = qa_geometry.check_safe_zone([_box("a", 108, 288, 864, 1345)], STORY_SIZE, STORY_ZONE)
    assert (issue["level"], issue["code"], issue["id"]) == ("error", "GATE_FAILED", "a") and issue["msg"]
def test_mixed_boxes_reports_bad_id():
    from forja import qa_geometry
    boxes = [_box("boa", 108, 288, 864, 1344), _box("ruim", 107, 288, 864, 1344)]
    (issue,) = qa_geometry.check_safe_zone(boxes, STORY_SIZE, STORY_ZONE)
    assert (issue["level"], issue["code"], issue["id"]) == ("error", "GATE_FAILED", "ruim") and issue["msg"]
def test_feed_exact_zone_passes():
    from forja import qa_geometry
    assert qa_geometry.check_safe_zone([_box("a", 54, 68, 972, 1214)], FEED_SIZE, FEED_ZONE) == []
def test_feed_top_breach_fails():
    from forja import qa_geometry
    (issue,) = qa_geometry.check_safe_zone([_box("a", 54, 67, 972, 1214)], FEED_SIZE, FEED_ZONE)
    assert (issue["level"], issue["code"], issue["id"]) == ("error", "GATE_FAILED", "a") and issue["msg"]
def test_missing_left_raises_config_invalid():
    from forja import qa_geometry
    from forja.errors import ForjaError
    with pytest.raises(ForjaError) as exc:
        qa_geometry.check_safe_zone([_box("a", 108, 288, 864, 1344)], STORY_SIZE, {"top": 0.15, "bottom": 0.15, "right": 0.10})
    assert exc.value.code == "CONFIG_INVALID"
def test_negative_fraction_raises_config_invalid():
    from forja import qa_geometry
    from forja.errors import ForjaError
    with pytest.raises(ForjaError) as exc:
        qa_geometry.check_safe_zone([_box("a", 108, 288, 864, 1344)], STORY_SIZE, {"top": -0.1, "bottom": 0.15, "left": 0.10, "right": 0.10})
    assert exc.value.code == "CONFIG_INVALID"
def test_half_fraction_raises_config_invalid():
    from forja import qa_geometry
    from forja.errors import ForjaError
    with pytest.raises(ForjaError) as exc:
        qa_geometry.check_safe_zone([_box("a", 108, 288, 864, 1344)], STORY_SIZE, {"top": 0.5, "bottom": 0.15, "left": 0.10, "right": 0.10})
    assert exc.value.code == "CONFIG_INVALID"
def test_string_fraction_raises_config_invalid():
    from forja import qa_geometry
    from forja.errors import ForjaError
    with pytest.raises(ForjaError) as exc:
        qa_geometry.check_safe_zone([_box("a", 108, 288, 864, 1344)], STORY_SIZE, {"top": "0.1", "bottom": 0.15, "left": 0.10, "right": 0.10})
    assert exc.value.code == "CONFIG_INVALID"
def test_none_zone_raises_config_invalid():
    from forja import qa_geometry
    from forja.errors import ForjaError
    with pytest.raises(ForjaError) as exc:
        qa_geometry.check_safe_zone([_box("a", 108, 288, 864, 1344)], STORY_SIZE, None)
    assert exc.value.code == "CONFIG_INVALID"
def test_empty_boxes_pass():
    from forja import qa_geometry
    assert qa_geometry.check_safe_zone([], STORY_SIZE, STORY_ZONE) == []
def test_none_boxes_pass():
    from forja import qa_geometry
    assert qa_geometry.check_safe_zone(None, STORY_SIZE, STORY_ZONE) == []
def test_safe_area_regression_margin_48():
    from forja import qa_geometry
    (issue,) = qa_geometry.check_safe_area([_box("a", 47, 48, 10, 10)], STORY_SIZE)
    assert (issue["level"], issue["code"]) == ("error", "GATE_FAILED") and issue["msg"]
    assert qa_geometry.check_safe_area([_box("a", 48, 48, 10, 10)], STORY_SIZE) == []
