"""Ambiente para subprocessos: sem variaveis com cara de segredo."""
from __future__ import annotations

import os

_SECRET_PARTS = {"KEY", "TOKEN", "SECRET", "SECRETS", "PASSWORD", "CREDENTIAL", "CREDENTIALS"}


def _is_secret_name(name: str) -> bool:
    upper = str(name).upper()
    return any(part in _SECRET_PARTS for part in upper.split("_"))


def sanitized(env=None) -> dict:
    """Copia o ambiente removendo chaves/tokens/senhas.

    O TTS roda no processo Python (le a chave do ambiente do projeto); ffmpeg,
    ffprobe, Remotion e Chrome nao precisam dela e nao devem herda-la.
    """
    source = os.environ if env is None else env
    return {name: value for name, value in source.items() if not _is_secret_name(name)}
