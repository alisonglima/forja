"""Contrato da prova (c): preflight provocado em `p5-03-preflight/`.

Para estouro/contraste/safe/ppi o comando grava `check-<caso>.json`,
`check-<caso>.log` e `exit-<caso>.txt`; o controle grava
`check-controle.json` e `exit-controle.txt` (plano:2263-2277). Todo JSON
parseia e contém, sem schema e recursivamente, `overflow`, `contrast`,
`safe-area` ou `image-ppi` (plano:2278); os quatro dão exit 1 e o controle
exit 0 sem erro. O `.mjs`/`.sh` só executa e grava (plano:2347-2350,2386).
# LACUNA: schema do JSON, logs, hash e controle não fixados; hash só se
# `sha256sums.txt` existir.
# DIVERGENCIA: comando em `p5-03/` (plano:2265-2275) x árvore
# `p5-03-preflight/` (plano:2355); adotada a árvore.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

CASOS = {"estouro": "overflow", "contraste": "contrast", "safe": "safe-area", "ppi": "image-ppi"}
CHECK = set(CASOS) | {"controle"}


def _sha(valor):
    return hashlib.sha256(valor.encode() if isinstance(valor, str) else valor).hexdigest()


def _tem_erro(obj):
    if isinstance(obj, dict):
        if str(obj.get("level", obj.get("severity", ""))).lower() in {"error", "erro"}:
            return True
        return any(
            (str(chave).lower() in {"errors", "erros"} and bool(valor)) or _tem_erro(valor)
            for chave, valor in obj.items()
        )
    return any(_tem_erro(valor) for valor in obj) if isinstance(obj, list) else False


def validar(ev):
    """Lista problemas; ev = dict nome->conteúdo ou caminho da pasta da prova."""
    if not isinstance(ev, dict):
        raiz = Path(ev)
        if not raiz.is_dir():
            return [f"diretório ausente: {raiz}"]
        ev = {p.relative_to(raiz).as_posix(): p.read_bytes() for p in raiz.rglob("*") if p.is_file()}
    problemas = []

    def texto(nome):
        valor = ev.get(nome)
        if valor is None:
            problemas.append(f"arquivo ausente: {nome}")
            return None
        return valor.decode("utf-8", "replace") if isinstance(valor, bytes) else str(valor)

    for caso in CHECK:
        nome = f"check-{caso}.json"
        bruto = texto(nome)
        if bruto is not None:
            try:
                dados = json.loads(bruto)
            except (json.JSONDecodeError, ValueError):
                problemas.append(f"{nome}: JSON inválido")
            else:
                if caso == "controle" and _tem_erro(dados):
                    problemas.append(f"{nome}: controle com erro")
                elif caso != "controle" and CASOS[caso] not in json.dumps(dados).lower():
                    problemas.append(f"{nome}: código {CASOS[caso]} ausente")
        if caso != "controle":
            texto(f"check-{caso}.log")
        saida = texto(f"exit-{caso}.txt")
        if saida is not None:
            try:
                codigo = int(saida.strip())
            except ValueError:
                problemas.append(f"exit-{caso}.txt: inteiro inválido")
            else:
                esperado = 0 if caso == "controle" else 1
                if codigo != esperado:
                    problemas.append(f"exit-{caso}.txt: {codigo}, esperado {esperado}")

    manifesto = ev.get("sha256sums.txt")
    if manifesto is not None:
        bruto = manifesto.decode("utf-8", "replace") if isinstance(manifesto, bytes) else str(manifesto)
        for linha in filter(str.strip, bruto.splitlines()):
            partes = linha.split()
            if len(partes) < 2 or len(partes[0]) != 64:
                problemas.append(f"sha256sums.txt: hash ausente/inválido: {linha!r}")
                continue
            nome = partes[-1].lstrip("*")
            if nome not in ev:
                problemas.append(f"sha256sums.txt: arquivo ausente: {nome}")
            elif _sha(ev[nome]) != partes[0].lower():
                problemas.append(f"sha256sums.txt: hash não confere: {nome}")
    return problemas


def _ev_valida():
    ev = {}
    for caso, codigo in CASOS.items():
        ev[f"check-{caso}.json"] = json.dumps({"issues": [{"rule": codigo, "level": "error"}]})
        ev[f"check-{caso}.log"] = ""
        ev[f"exit-{caso}.txt"] = "1\n"
    ev["check-controle.json"] = json.dumps({"ok": True, "issues": []})
    ev["exit-controle.txt"] = "0\n"
    ev["sha256sums.txt"] = "".join(f"{_sha(v)}  {k}\n" for k, v in ev.items())
    return ev


def test_contrato_amostra_valida():
    assert validar(_ev_valida()) == []


@pytest.mark.parametrize(
    "mutar,trecho",
    [
        (lambda ev: ev.pop("check-ppi.json"), "arquivo ausente: check-ppi.json"),
        (lambda ev: ev.pop("check-ppi.log"), "arquivo ausente: check-ppi.log"),
        (lambda ev: ev.update({"check-safe.json": '{"issues": []}'}), "safe-area ausente"),
        (lambda ev: ev.update({"exit-estouro.txt": "0\n"}), "exit-estouro.txt: 0"),
        (lambda ev: ev.update({"exit-controle.txt": "1\n"}), "exit-controle.txt: 1"),
        (lambda ev: ev.update({"check-estouro.json": ""}), "JSON inválido"),
        (lambda ev: ev.update({"check-estouro.json": '{"issues": ['}), "JSON inválido"),
        (lambda ev: ev.update({"sha256sums.txt": "check-estouro.json\n"}), "hash ausente"),
    ],
)
def test_contrato_defeitos(mutar, trecho):
    ev = _ev_valida()
    mutar(ev)
    assert any(trecho in p for p in validar(ev))


def test_contrato_controle_com_erro():
    ev = _ev_valida()
    ev["check-controle.json"] = '{"issues": [{"level": "error"}]}'
    assert any("controle com erro" in p for p in validar(ev))


def test_evidencia_real():
    if os.environ.get("FORJA_PROVA_KIT") != "1":
        pytest.skip("defina FORJA_PROVA_KIT=1 para ler a evidência real")
    raiz = Path(__file__).resolve().parents[2] / ".work/prova-kit/evidencias/p5-03-preflight"
    problemas = validar(raiz)
    assert problemas == [], "\n".join(problemas)
