from __future__ import annotations

# Codigos de erro da plataforma: exit code, se vale repetir e dica de correcao.
ERROR_CODES: dict[str, dict] = {
    "CONFIG_INVALID": {"exit": 2, "retryable": False, "hint": "corrija o config.yaml (rode `forja init` se necessario) e tente de novo"},
    "USAGE": {"exit": 2, "retryable": False, "hint": "confira os argumentos do comando com `forja --help`"},
    "GATE_FAILED": {"exit": 1, "retryable": False, "hint": "resolva as issues apontadas antes de entregar o video"},
    "PROVIDER_ERROR": {"exit": 3, "retryable": True, "hint": "falha do provedor externo; tente de novo em alguns instantes"},
    "RATE_LIMITED": {"exit": 3, "retryable": True, "hint": "cota atingida; aguarde e tente de novo"},
    "NETWORK": {"exit": 3, "retryable": True, "hint": "verifique a conexao e tente de novo"},
    "MISSING_PREREQ": {"exit": 4, "retryable": False, "hint": "instale o pre-requisito ausente e rode `forja doctor`"},
    "MISSING_KEY": {"exit": 4, "retryable": False, "hint": "defina a variavel de ambiente indicada (nunca grave o valor no projeto)"},
    "MISSING_INPUT": {"exit": 2, "retryable": False, "hint": "gere ou informe a entrada que falta e tente de novo"},
    "INTERNAL": {"exit": 5, "retryable": False, "hint": "erro interno; rode com --json e reporte o codigo e a mensagem"},
    "CONTRAST_PHOTO": {"exit": 1, "retryable": False, "hint": "escureça ou clareie a foto, ou mova o texto; meça de novo a região sob o texto"},
    "APPROVAL_STALE": {"exit": 1, "retryable": False, "hint": "o arquivo mudou depois da aprovação; revise e rode `forja approve` de novo com o hash novo"},
    "BRIEF_INCOMPLETE": {"exit": 2, "retryable": False, "hint": "preencha objetivo, público e tom no brief.yaml e aprove o brief"},
    "FORMAT_UNSUPPORTED": {"exit": 2, "retryable": False, "hint": "use um formato da matriz da marca (1080x1080, 1080x1350, 1080x1920, 1200x630, A4/A5 RGB)"},
    "QUOTA_EXHAUSTED": {"exit": 3, "retryable": False, "hint": "cota da conta esgotada; pare, registre no livro-razão e aguarde a janela"},
    "SESSION_LOST": {"exit": 3, "retryable": False, "hint": "sessão Google caiu; humano refaça o login no VNC e rode `forja google doctor`"},
    "UI_CHANGED": {"exit": 3, "retryable": False, "hint": "a interface mudou; atualize seletores e rode `forja google doctor` antes de repetir"},
    "ASSET_MISSING": {"exit": 2, "retryable": False, "hint": "o ativo não está no incoming/manifesto; baixe ou registre antes de compor"},
    "TEMPLATE_HASH_MISMATCH": {"exit": 1, "retryable": False, "hint": "o template mudou fora do OD; re-promova e re-aprove antes de renderizar"},
    "DUPLICATE_ARTIFACT": {"exit": 1, "retryable": False, "hint": "já existe arte com este hash nos últimos 30 dias; use a existente ou justifique"},
    "LOTE_TOO_BIG": {"exit": 2, "retryable": False, "hint": "reduza para até 200 linhas e 400 arquivos; divida o lote"},
    "NAME_COLLISION": {"exit": 2, "retryable": False, "hint": "nomes geram o mesmo slug; ajuste a coluna de nome ou use sufixo"},
    "BRAND_VARIANT_REQUIRED": {"exit": 2, "retryable": False, "hint": "declare `variant` no brief/deck; a marca tem mais de uma variante"},
    "DECK_SCHEMA": {"exit": 2, "retryable": False, "hint": "corrija as chaves e os tipos do deck e rode de novo"},
    "DECK_TEMPLATE_MISSING": {"exit": 4, "retryable": False, "hint": "o template base do deck não está no kit; instale o template e repita"},
    "DECK_SHAPE_MISSING": {"exit": 1, "retryable": False, "hint": "o slide de origem não tem a forma pedida; escolha outro modelo ou ajuste o slide"},
    "DECK_CONVERT_FAILED": {"exit": 3, "retryable": True, "hint": "a conversão do deck falhou; tente de novo e, se persistir, reporte"},
    "ASSET_HASH_MISMATCH": {"exit": 1, "retryable": False, "hint": "o hash do ativo não confere com o manifesto; re-registre o ativo antes de compor"},
}


class ForjaError(Exception):
    """Erro com codigo estavel, exit code e dica para o usuario."""

    def __init__(self, code, msg, hint=None, details=None):
        self.code = code if code in ERROR_CODES else "INTERNAL"
        meta = ERROR_CODES[self.code]
        self.msg = msg
        self.hint = meta["hint"] if hint is None else hint
        self.details = details
        self.exit_code = meta["exit"]
        self.retryable = meta["retryable"]
        super().__init__(msg)


def error_payload(exc) -> dict:
    """Envelope JSON de falha; nunca inclui traceback."""
    if not isinstance(exc, ForjaError):
        exc = ForjaError("INTERNAL", str(exc))
    return {
        "ok": False,
        "error": {
            "code": exc.code,
            "msg": exc.msg,
            "hint": exc.hint,
            "retryable": exc.retryable,
            "details": exc.details,
        },
    }
