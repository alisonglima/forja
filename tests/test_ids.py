"""Ids usados em nomes de arquivo precisam ser seguros (sem / nem ..)."""
import pytest


def test_accepts_normal_ids():
    from forja import ids

    for value in ("A", "cena-1", "cena_1.v2", "123"):
        assert ids.is_safe_id(value), value


def test_rejects_path_like_ids():
    from forja import ids

    for value in ("", "..", "../x", "a/b", "a\\b", "a..b", "x y", None, 3):
        assert not ids.is_safe_id(value), value


def test_require_safe_id_raises_config_invalid():
    from forja import ids
    from forja.errors import ForjaError

    with pytest.raises(ForjaError) as excinfo:
        ids.require_safe_id("../../PWNED", "id da cena")
    assert excinfo.value.code == "CONFIG_INVALID"
    assert "id da cena" in str(excinfo.value)
