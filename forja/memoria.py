"""Memoria de correcoes: registro, propostas de regra e decisoes do dono."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .errors import ForjaError
from .ids import require_safe_id

_ARQUIVO = "memoria-correcoes.jsonl"
_DECISOES, _CAMPOS = "decisoes.jsonl", ("antes", "depois", "motivo", "por", "padrao", "hash")


def _hash(antes: str, depois: str) -> str:
    return hashlib.sha256(("%s\x00%s" % (antes, depois)).encode("utf-8")).hexdigest()


def _texto(valor, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ForjaError("CONFIG_INVALID", "correcao.%s deve ser texto nao vazio" % campo)
    return valor.strip()


def _ler(caminho: Path) -> list[dict]:
    if not caminho.is_file():
        return []
    try:
        bruto = caminho.read_text(encoding="utf-8")
    except OSError as exc:
        raise ForjaError("CONFIG_INVALID", "memoria ilegivel: %s" % exc) from exc
    if not bruto:
        return []
    if not bruto.endswith("\n"):
        raise ForjaError("CONFIG_INVALID", "memoria truncada: falta quebra de linha final")
    registros = []
    for numero, linha in enumerate(bruto.splitlines(), 1):
        if not linha.strip():
            continue
        try:
            dado = json.loads(linha)
        except ValueError as exc:
            raise ForjaError("CONFIG_INVALID", "memoria truncada na linha %d" % numero) from exc
        if not isinstance(dado, dict) or any(not isinstance(dado.get(c), str) for c in _CAMPOS):
            raise ForjaError("CONFIG_INVALID", "registro invalido na linha %d" % numero)
        if dado["hash"] != _hash(dado["antes"], dado["depois"]):
            raise ForjaError("CONFIG_INVALID", "hash nao confere na linha %d" % numero)
        registros.append(dado)
    return registros


def _escrever(caminho: Path, dado: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dado, ensure_ascii=False) + "\n")


def _proposta(raiz: Path, padrao: str, registros: list[dict]) -> None:
    ocorrencias = [r for r in registros if r["padrao"] == padrao]
    linhas = [
        "# Proposta de regra: %s" % padrao,
        "",
        "Sugestao gerada apos %d ocorrencias do mesmo padrao." % len(ocorrencias),
        "Nao entra no lint sem aprovacao do dono.",
        "",
        "## Escopo",
        "",
        "Padrao `%s`, aplicado a correcoes de texto da marca." % padrao,
        "",
        "## Evidencia",
        "",
    ]
    for item in ocorrencias:
        linhas.append(
            "- antes: %s | depois: %s | motivo: %s | por: %s | hash: %s"
            % (item["antes"], item["depois"], item["motivo"], item["por"], item["hash"])
        )
    destino = raiz / "propostas" / ("regra-%s.md" % padrao)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(linhas), encoding="utf-8")


def registrar_correcao(root, *, antes, depois, motivo, por, padrao) -> dict:
    """Grava uma correcao humana e sugere regra na terceira ocorrencia."""
    raiz = Path(root)
    padrao = require_safe_id(_texto(padrao, "padrao"), "padrao")
    dado = {
        "antes": _texto(antes, "antes"),
        "depois": _texto(depois, "depois"),
        "motivo": _texto(motivo, "motivo"),
        "por": _texto(por, "por"),
        "padrao": padrao,
    }
    dado["hash"] = _hash(dado["antes"], dado["depois"])
    caminho = raiz / _ARQUIVO
    registros = _ler(caminho)
    registros.append(dado)
    _escrever(caminho, dado)
    if sum(1 for r in registros if r["padrao"] == padrao) >= 3:
        _proposta(raiz, padrao, registros)
    return dado


def decidir_proposta(root, regra, *, decisao, por) -> dict:
    """Registra a decisao do dono e arquiva a proposta rejeitada."""
    raiz = Path(root)
    regra = require_safe_id(_texto(regra, "regra"), "regra")
    por = _texto(por, "por")
    if decisao not in ("aprovar", "rejeitar"):
        raise ForjaError("USAGE", "decisao deve ser aprovar ou rejeitar")
    proposta = raiz / "propostas" / regra
    if not proposta.is_file():
        raise ForjaError("MISSING_INPUT", "proposta ausente: %s" % regra)
    if decisao == "rejeitar":
        arquivo = raiz / "propostas" / "arquivadas" / regra
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        proposta.replace(arquivo)
    dec = {"regra": regra, "decisao": decisao, "por": por}
    _escrever(raiz / "propostas" / _DECISOES, dec)
    return dec
