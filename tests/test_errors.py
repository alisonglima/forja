"""Contratos de forja.errors descritos no DESIGN.md."""
import json

import pytest

EXPECTED_EXITS = {
    "CONFIG_INVALID": 2,
    "USAGE": 2,
    "GATE_FAILED": 1,
    "PROVIDER_ERROR": 3,
    "RATE_LIMITED": 3,
    "NETWORK": 3,
    "MISSING_PREREQ": 4,
    "MISSING_KEY": 4,
    "MISSING_INPUT": 2,
    "INTERNAL": 5,
}


def test_error_codes_has_exactly_the_documented_codes():
    from forja import errors

    assert set(errors.ERROR_CODES) == set(EXPECTED_EXITS)


@pytest.mark.parametrize("code,exit_code", sorted(EXPECTED_EXITS.items()))
def test_error_codes_have_documented_exit_codes(code, exit_code):
    from forja import errors

    assert errors.ERROR_CODES[code]["exit"] == exit_code


def test_error_codes_entries_have_only_documented_fields():
    from forja import errors

    assert all(
        set(meta) == {"exit", "retryable", "hint"}
        for meta in errors.ERROR_CODES.values()
    )


def test_error_codes_fields_have_documented_types():
    from forja import errors

    assert all(
        isinstance(meta["exit"], int)
        and isinstance(meta["retryable"], bool)
        and isinstance(meta["hint"], str)
        for meta in errors.ERROR_CODES.values()
    )


@pytest.mark.parametrize(
    "code,retryable",
    [
        ("PROVIDER_ERROR", True),
        ("RATE_LIMITED", True),
        ("NETWORK", True),
        ("CONFIG_INVALID", False),
        ("USAGE", False),
        ("GATE_FAILED", False),
        ("MISSING_PREREQ", False),
        ("MISSING_KEY", False),
        ("MISSING_INPUT", False),
        ("INTERNAL", False),
    ],
)
def test_error_codes_retryable_follows_external_failure_class(code, retryable):
    from forja import errors

    assert errors.ERROR_CODES[code]["retryable"] is retryable


def test_forja_error_is_an_exception():
    from forja import errors

    assert issubclass(errors.ForjaError, Exception)


def test_forja_error_defaults_come_from_error_codes():
    from forja import errors

    exc = errors.ForjaError("USAGE", "faltou argumento")
    meta = errors.ERROR_CODES["USAGE"]
    assert (exc.code, exc.msg, exc.hint, exc.details, exc.exit_code, exc.retryable) == (
        "USAGE",
        "faltou argumento",
        meta["hint"],
        None,
        meta["exit"],
        meta["retryable"],
    )


def test_forja_error_accepts_explicit_hint():
    from forja import errors

    exc = errors.ForjaError("CONFIG_INVALID", "config ruim", hint="rode forja init")
    assert exc.hint == "rode forja init"


def test_forja_error_keeps_details():
    from forja import errors

    exc = errors.ForjaError(
        "CONFIG_INVALID", "config ruim", details={"campo": "voices.provider"}
    )
    assert exc.details == {"campo": "voices.provider"}


def test_forja_error_unknown_code_falls_back_to_internal():
    from forja import errors

    exc = errors.ForjaError("NAO_EXISTE", "boom")
    assert (exc.code, exc.exit_code, exc.retryable) == ("INTERNAL", 5, False)


def test_error_payload_has_documented_shape():
    from forja import errors

    payload = errors.error_payload(errors.ForjaError("USAGE", "x"))
    assert (set(payload), set(payload["error"])) == (
        {"ok", "error"},
        {"code", "msg", "hint", "retryable", "details"},
    )


def test_error_payload_reflects_forja_error_fields():
    from forja import errors

    exc = errors.ForjaError(
        "MISSING_KEY", "sem chave", hint="defina X", details={"env": "X"}
    )
    assert errors.error_payload(exc) == {
        "ok": False,
        "error": {
            "code": "MISSING_KEY",
            "msg": "sem chave",
            "hint": "defina X",
            "retryable": False,
            "details": {"env": "X"},
        },
    }


def test_error_payload_wraps_plain_exception_as_internal():
    from forja import errors

    payload = errors.error_payload(RuntimeError("quebrou"))
    assert (payload["error"]["code"], payload["error"]["msg"]) == (
        "INTERNAL",
        "quebrou",
    )


def test_error_payload_never_includes_a_traceback():
    from forja import errors

    assert "Traceback" not in json.dumps(
        errors.error_payload(RuntimeError("quebrou"))
    )


def test_error_payload_is_json_serializable():
    from forja import errors

    payload = errors.error_payload(
        errors.ForjaError("PROVIDER_ERROR", "rede", details={"status": 500})
    )
    assert json.loads(json.dumps(payload)) == payload
