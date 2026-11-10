from __future__ import annotations

# Codigos de erro da plataforma: exit code, se vale repetir e dica de correcao.
ERROR_CODES: dict[str, dict] = {
    "CONFIG_INVALID": {
        "exit": 2,
        "retryable": False,
        "hint": "corrija o config.yaml (rode `forja init` se necessario) e tente de novo",
    },
    "USAGE": {
        "exit": 2,
        "retryable": False,
        "hint": "confira os argumentos do comando com `forja --help`",
    },
    "GATE_FAILED": {
        "exit": 1,
        "retryable": False,
        "hint": "resolva as issues apontadas antes de entregar o video",
    },
    "PROVIDER_ERROR": {
        "exit": 3,
        "retryable": True,
        "hint": "falha do provedor externo; tente de novo em alguns instantes",
    },
    "RATE_LIMITED": {
        "exit": 3,
        "retryable": True,
        "hint": "cota atingida; aguarde e tente de novo",
    },
    "NETWORK": {
        "exit": 3,
        "retryable": True,
        "hint": "verifique a conexao e tente de novo",
    },
    "MISSING_PREREQ": {
        "exit": 4,
        "retryable": False,
        "hint": "instale o pre-requisito ausente e rode `forja doctor`",
    },
    "MISSING_KEY": {
        "exit": 4,
        "retryable": False,
        "hint": "defina a variavel de ambiente indicada (nunca grave o valor no projeto)",
    },
    "MISSING_INPUT": {
        "exit": 2,
        "retryable": False,
        "hint": "gere ou informe a entrada que falta e tente de novo",
    },
    "INTERNAL": {
        "exit": 5,
        "retryable": False,
        "hint": "erro interno; rode com --json e reporte o codigo e a mensagem",
    },
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
