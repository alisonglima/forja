"""Contratos de forja.registry descritos no DESIGN.md."""
import importlib.metadata
import json

import pytest


@pytest.fixture(autouse=True)
def _clean_registry():
    from forja import registry

    registry.reset_for_tests()
    yield
    registry.reset_for_tests()


def _entry(entries, name):
    return next(item for item in entries if item["name"] == name)


def test_kinds_are_the_documented_tuple():
    from forja import registry

    assert registry.KINDS == ("tts", "stt", "render", "clip", "image", "music")


def test_register_returns_the_decorated_object():
    from forja import registry

    def factory():
        return "ok"

    assert registry.register("tts", "alpha")(factory) is factory


def test_get_returns_registered_factory():
    from forja import registry

    def factory():
        return "ok"

    registry.register("tts", "alpha")(factory)
    assert registry.get("tts", "alpha") is factory


def test_register_rejects_unknown_kind():
    from forja import registry

    with pytest.raises(ValueError):
        registry.register("bogus", "alpha")(lambda: None)


def test_register_rejects_duplicate_name_in_same_kind():
    from forja import registry

    registry.register("tts", "alpha")(lambda: None)
    with pytest.raises(ValueError):
        registry.register("tts", "alpha")(lambda: None)


def test_same_name_is_allowed_in_different_kinds():
    from forja import registry

    first = lambda: "tts"
    second = lambda: "stt"
    registry.register("tts", "alpha")(first)
    registry.register("stt", "alpha")(second)
    assert (registry.get("tts", "alpha"), registry.get("stt", "alpha")) == (
        first,
        second,
    )


def test_get_unknown_provider_raises_config_invalid():
    from forja import errors, registry

    with pytest.raises(errors.ForjaError) as info:
        registry.get("tts", "ghost")
    assert info.value.code == "CONFIG_INVALID"


def test_get_error_lists_available_names():
    from forja import errors, registry

    for name in ("alpha", "beta"):
        registry.register("tts", name)(lambda: None)
    with pytest.raises(errors.ForjaError) as info:
        registry.get("tts", "ghost")
    text = "%s %s" % (info.value.msg, info.value.hint or "")
    assert "alpha" in text and "beta" in text


def test_available_entry_has_documented_keys():
    from forja import registry

    registry.register("tts", "alpha")(lambda: None)
    assert set(registry.available(env={})[0]) == {
        "kind",
        "name",
        "requires_env",
        "env_ok",
        "network",
        "note",
    }


def test_available_filters_by_kind():
    from forja import registry

    registry.register("tts", "alpha")(lambda: None)
    registry.register("stt", "beta")(lambda: None)
    assert [item["name"] for item in registry.available("tts", env={})] == ["alpha"]


def test_available_without_kind_lists_every_kind():
    from forja import registry

    registry.register("tts", "alpha")(lambda: None)
    registry.register("stt", "beta")(lambda: None)
    entries = registry.available(env={})
    assert {(item["kind"], item["name"]) for item in entries} == {
        ("tts", "alpha"),
        ("stt", "beta"),
    }


def test_available_env_ok_true_when_all_required_vars_are_set():
    from forja import registry

    registry.register(
        "tts", "alpha", requires_env=("FORJA_TEST_A", "FORJA_TEST_B")
    )(lambda: None)
    entry = _entry(
        registry.available(env={"FORJA_TEST_A": "1", "FORJA_TEST_B": "2"}), "alpha"
    )
    assert entry["env_ok"] is True


def test_available_env_ok_false_when_a_required_var_is_missing():
    from forja import registry

    registry.register(
        "tts", "alpha", requires_env=("FORJA_TEST_A", "FORJA_TEST_B")
    )(lambda: None)
    entry = _entry(registry.available(env={"FORJA_TEST_A": "1"}), "alpha")
    assert entry["env_ok"] is False


def test_available_env_ok_false_when_a_required_var_is_empty():
    from forja import registry

    registry.register("tts", "alpha", requires_env=("FORJA_TEST_A",))(lambda: None)
    entry = _entry(registry.available(env={"FORJA_TEST_A": ""}), "alpha")
    assert entry["env_ok"] is False


def test_available_never_exposes_env_values():
    from forja import registry

    registry.register("tts", "alpha", requires_env=("FORJA_TEST_TOKEN",))(
        lambda: None
    )
    env = {"FORJA_TEST_TOKEN": "sentinela"}
    assert "sentinela" not in json.dumps(registry.available(env=env))


def test_available_reports_requires_env_network_and_note():
    from forja import registry

    registry.register(
        "render", "alpha", requires_env=("FORJA_TEST_A",), network=True, note="nota"
    )(lambda: None)
    entry = _entry(registry.available(env={"FORJA_TEST_A": "x"}), "alpha")
    assert (set(entry["requires_env"]), entry["network"], entry["note"]) == (
        {"FORJA_TEST_A"},
        True,
        "nota",
    )


def test_reset_for_tests_clears_registry():
    from forja import errors, registry

    registry.register("tts", "alpha")(lambda: None)
    registry.reset_for_tests()
    with pytest.raises(errors.ForjaError):
        registry.get("tts", "alpha")


def test_load_entry_points_failure_becomes_available_warning(monkeypatch):
    from forja import registry

    class BrokenEntryPoint:
        name = "broken"
        group = "forja.providers"
        value = "plugin_quebrado:factory"

        def load(self):
            raise RuntimeError("plugin quebrado")

    class FakeEntryPoints(list):
        def select(self, **kwargs):
            return self

        def get(self, group, default=None):
            return self

    def fake_entry_points(*args, **kwargs):
        return FakeEntryPoints([BrokenEntryPoint()])

    monkeypatch.setattr(importlib.metadata, "entry_points", fake_entry_points)
    if hasattr(registry, "entry_points"):
        monkeypatch.setattr(registry, "entry_points", fake_entry_points)

    registry.load_entry_points("forja.providers")
    assert any("error" in item for item in registry.available())
