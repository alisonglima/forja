"""Contrato de forja.errors para L-ERR-01 (T-ERR-01).

Congela a tabela final de 28 codigos: os 10 herdados (DESIGN.md:205-207),
os 13 de plano:469-481 e os 5 de slide de plano:1702. Cada entrada tem
exatamente {"exit", "retryable", "hint"} (plano:399-407; plano:465), com
exit 0..5 e retryable da tabela. Os hints de plano:469-481 sao literais; o
texto dos 5 de slide nao e dado, so a existencia. ForjaError le defaults da
tabela e codigo desconhecido vira INTERNAL (DESIGN.md:206-208).
FORMAT_STALE e FORMAT_UNVERIFIED nao entram nesta lane (plano:334).
"""
import pytest

EXPECTED = {
    "CONFIG_INVALID": (2, False), "USAGE": (2, False), "GATE_FAILED": (1, False), "PROVIDER_ERROR": (3, True),
    "RATE_LIMITED": (3, True), "NETWORK": (3, True), "MISSING_PREREQ": (4, False), "MISSING_KEY": (4, False),
    "MISSING_INPUT": (2, False), "INTERNAL": (5, False), "CONTRAST_PHOTO": (1, False), "APPROVAL_STALE": (1, False),
    "BRIEF_INCOMPLETE": (2, False), "FORMAT_UNSUPPORTED": (2, False), "QUOTA_EXHAUSTED": (3, False), "SESSION_LOST": (3, False),
    "UI_CHANGED": (3, False), "ASSET_MISSING": (2, False), "TEMPLATE_HASH_MISMATCH": (1, False), "DUPLICATE_ARTIFACT": (1, False),
    "LOTE_TOO_BIG": (2, False), "NAME_COLLISION": (2, False), "BRAND_VARIANT_REQUIRED": (2, False), "DECK_SCHEMA": (2, False),
    "DECK_TEMPLATE_MISSING": (4, False), "DECK_SHAPE_MISSING": (1, False), "DECK_PLACEHOLDER_LEFT": (1, False), "DECK_CONVERT_FAILED": (3, True), "ASSET_HASH_MISMATCH": (1, False),
}

NEW_HINTS = {
    "CONTRAST_PHOTO": "escureça ou clareie a foto, ou mova o texto; meça de novo a região sob o texto",
    "APPROVAL_STALE": "o arquivo mudou depois da aprovação; revise e rode `forja approve` de novo com o hash novo",
    "BRIEF_INCOMPLETE": "preencha objetivo, público e tom no brief.yaml e aprove o brief",
    "FORMAT_UNSUPPORTED": "use um formato da matriz da marca (1080x1080, 1080x1350, 1080x1920, 1200x630, A4/A5 RGB)",
    "QUOTA_EXHAUSTED": "cota da conta esgotada; pare, registre no livro-razão e aguarde a janela",
    "SESSION_LOST": "sessão Google caiu; humano refaça o login no VNC e rode `forja google doctor`",
    "UI_CHANGED": "a interface mudou; atualize seletores e rode `forja google doctor` antes de repetir",
    "ASSET_MISSING": "o ativo não está no incoming/manifesto; baixe ou registre antes de compor",
    "TEMPLATE_HASH_MISMATCH": "o template mudou fora do OD; re-promova e re-aprove antes de renderizar",
    "DUPLICATE_ARTIFACT": "já existe arte com este hash nos últimos 30 dias; use a existente ou justifique",
    "LOTE_TOO_BIG": "reduza para até 200 linhas e 400 arquivos; divida o lote",
    "NAME_COLLISION": "nomes geram o mesmo slug; ajuste a coluna de nome ou use sufixo",
    "BRAND_VARIANT_REQUIRED": "declare `variant` no brief/deck; a marca tem mais de uma variante",
}

# LACUNA: plano:1702 exige hint e retryable dos 5 codigos de slide, mas nao
# fixa o texto do hint nem o retryable de DECK_TEMPLATE_MISSING,
# DECK_SHAPE_MISSING e ASSET_HASH_MISMATCH; aqui: hint nao vazio e retryable
# false pelo exit 1/2/4 (plano:399-407). plano:483 diz que nenhum codigo novo
# usa exit 4, mas plano:1702 fixa DECK_TEMPLATE_MISSING em 4; vale o slide.

def test_error_codes_has_exactly_the_28_contract_codes():
    from forja import errors

    assert set(errors.ERROR_CODES) == set(EXPECTED)

def test_error_codes_entries_have_only_the_three_contract_fields():
    from forja import errors

    assert all(set(meta) == {"exit", "retryable", "hint"} for meta in errors.ERROR_CODES.values())

def test_error_codes_fields_have_contract_types_and_non_empty_hints():
    from forja import errors

    assert all(
        isinstance(meta["exit"], int) and not isinstance(meta["exit"], bool)
        and isinstance(meta["retryable"], bool)
        and isinstance(meta["hint"], str) and meta["hint"].strip()
        for meta in errors.ERROR_CODES.values()
    )

@pytest.mark.parametrize("code,exit_code,retryable", sorted((c, *v) for c, v in EXPECTED.items()))
def test_error_codes_exit_and_retryable_follow_contract(code, exit_code, retryable):
    from forja import errors

    assert (errors.ERROR_CODES[code]["exit"], errors.ERROR_CODES[code]["retryable"]) == (exit_code, retryable)

@pytest.mark.parametrize("code,hint", sorted(NEW_HINTS.items()))
def test_new_error_hints_are_literal_contract_text(code, hint):
    from forja import errors

    assert errors.ERROR_CODES[code]["hint"] == hint

@pytest.mark.parametrize("code", sorted(EXPECTED))
def test_forja_error_defaults_come_from_each_contract_entry(code):
    from forja import errors

    exc = errors.ForjaError(code, "falhou")
    meta = errors.ERROR_CODES[code]
    assert (exc.code, exc.msg, exc.exit_code, exc.retryable, exc.hint) == (
        code, "falhou", meta["exit"], meta["retryable"], meta["hint"],
    )

def test_unknown_and_empty_codes_fall_back_to_internal():
    from forja import errors

    for code in ("NAO_EXISTE", ""):
        exc = errors.ForjaError(code, "boom")
        assert (exc.code, exc.exit_code, exc.retryable) == ("INTERNAL", 5, False)

def test_error_payload_for_a_new_code_has_exact_shape_and_values():
    from forja import errors

    exc = errors.ForjaError(
        "APPROVAL_STALE", "hash mudou", details={"expected": "a", "current": "b"}
    )
    assert errors.error_payload(exc) == {
        "ok": False,
        "error": {
            "code": "APPROVAL_STALE",
            "msg": "hash mudou",
            "hint": NEW_HINTS["APPROVAL_STALE"],
            "retryable": False,
            "details": {"expected": "a", "current": "b"},
        },
    }

def test_plain_exception_payload_is_internal_without_traceback():
    from forja import errors

    payload = errors.error_payload(RuntimeError("quebrou"))
    assert payload["error"] == {
        "code": "INTERNAL", "msg": "quebrou", "retryable": False, "details": None,
        "hint": errors.ERROR_CODES["INTERNAL"]["hint"],
    }
