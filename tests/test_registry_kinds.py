"""Contrato de forja.registry para os seis kinds de provedor.

plano:701 fixa KINDS == ("tts", "stt", "render", "clip", "image", "music").
clip segue como video gerado/baixado e video_gen nao existe (plano:700).
register e available validam o tuple e listam os seis na mensagem (plano:700, 1093).
image e music sao namespaces proprios, sem colisao com a camada clip (plano:701, 1128).
O tuple antigo de tests/test_registry.py fica para a lane T-REG-LEG (plano:820).
"""
import pytest


@pytest.fixture(autouse=True)
def _clean_registry():
    from forja import registry

    registry.reset_for_tests()
    yield
    registry.reset_for_tests()


def _kind_error(kind):
    return ("kind de provedor invalido: %r (use um de: "
            "tts, stt, render, clip, image, music)" % kind)


def test_kinds_are_the_six_documented_provider_kinds():
    from forja import registry
    assert registry.KINDS == ("tts", "stt", "render", "clip", "image", "music")


@pytest.mark.parametrize("kind", ["tts", "stt", "render", "clip", "image", "music"])
def test_register_and_get_accept_each_of_the_six_kinds(kind):
    from forja import registry

    def factory():
        return kind

    assert registry.register(kind, "probe")(factory) is factory
    assert registry.get(kind, "probe") is factory


def test_register_rejects_video_gen_with_the_six_kinds_listed():
    from forja import registry
    with pytest.raises(ValueError) as info:
        registry.register("video_gen", "x")(lambda: None)
    assert str(info.value) == _kind_error("video_gen")


def test_available_rejects_unknown_kind_with_the_same_message():
    from forja import registry
    with pytest.raises(ValueError) as info:
        registry.available("video_gen", env={})
    assert str(info.value) == _kind_error("video_gen")


def test_available_lists_image_and_music_in_kinds_order():
    from forja import registry
    registry.register("image", "google_flow", network=True, note="opt-in")(lambda: None)
    registry.register("music", "google_flow_music", network=True, note="opt-in")(lambda: None)
    assert registry.available(env={}) == [
        {"kind": "image", "name": "google_flow", "requires_env": (), "env_ok": True,
         "network": True, "note": "opt-in"},
        {"kind": "music", "name": "google_flow_music", "requires_env": (), "env_ok": True,
         "network": True, "note": "opt-in"},
    ]


def test_available_filters_music_and_checks_requires_env():
    from forja import registry
    registry.register("image", "still")(lambda: None)
    registry.register("music", "needs_token", requires_env=("TOKEN",))(lambda: None)
    assert registry.available("music", env={"TOKEN": "segredo"}) == [
        {"kind": "music", "name": "needs_token", "requires_env": ("TOKEN",),
         "env_ok": True, "network": False, "note": ""},
    ]


def test_available_on_empty_registry_is_empty():
    from forja import registry
    assert registry.available(env={}) == []
