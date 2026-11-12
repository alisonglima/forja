"""Validacao do lote digital: CSV/JSON -> plano de artes (limite 200x400)."""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path

from .. import formats
from ..errors import ForjaError

MAX_LINHAS = 200
MAX_ARQUIVOS = 400
_COLUNAS = ("nome", "texto", "formato")
_NAO_SLUG = re.compile(r"[^a-z0-9]+")


def _fail(code, msg, **details):
    return ForjaError(code, msg, details=details or None)


def _path(value, label) -> Path:
    if value is None or not str(value).strip():
        raise _fail("MISSING_INPUT", "%s nao informada" % label)
    path = Path(value)
    if ".." in path.parts:
        raise _fail("CONFIG_INVALID", "%s com caminho hostil: %s" % (label, path),
                    path=str(path))
    return path


def slug(nome) -> str:
    texto = unicodedata.normalize("NFKD", str(nome or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    return _NAO_SLUG.sub("-", texto).strip("-")


def _matriz(formatos) -> list[str]:
    if formatos is None:
        return [str(row["id"]) for row in formats.load_formats()["formatos"]]
    if isinstance(formatos, (str, bytes)):
        raise _fail("CONFIG_INVALID", "formatos deve ser uma lista de ids")
    return [str(item).strip() for item in formatos]


def _ler_csv(path: Path) -> list[dict]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            colunas = [str(c or "").strip().lower() for c in reader.fieldnames or []]
            faltando = [c for c in _COLUNAS if c not in colunas]
            if faltando:
                raise _fail("CONFIG_INVALID",
                            "CSV sem as colunas: %s" % ", ".join(faltando),
                            path=str(path), columns=colunas)
            return [{str(k).strip().lower(): v for k, v in row.items() if k is not None}
                    for row in reader]
    except (OSError, UnicodeError, csv.Error) as exc:
        raise _fail("CONFIG_INVALID", "CSV ilegivel: %s" % path,
                    path=str(path), error=str(exc)) from exc


def _ler_json(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise _fail("MISSING_INPUT", "JSON ilegivel: %s" % path,
                    path=str(path), error=str(exc)) from exc
    if not isinstance(data, list):
        raise _fail("CONFIG_INVALID", "JSON deve ser uma lista de linhas",
                    path=str(path))
    if any(not isinstance(row, dict) for row in data):
        raise _fail("CONFIG_INVALID", "cada linha do JSON deve ser um objeto",
                    path=str(path))
    return [dict(row) for row in data]


def _ler_linhas(path: Path) -> list[dict]:
    if not path.is_file():
        raise _fail("MISSING_INPUT", "entrada ausente: %s" % path,
                    path=str(path))
    linhas = _ler_json(path) if path.suffix.lower() == ".json" else _ler_csv(path)
    linhas = [row for row in linhas if any(str(v or "").strip() for v in row.values())]
    if not linhas:
        raise _fail("MISSING_INPUT", "entrada vazia: %s" % path,
                    path=str(path))
    return linhas


def _plano(linhas: list[dict], matriz: list[str]) -> list[dict]:
    plano = []
    vistos: dict[str, str] = {}
    for numero, row in enumerate(linhas, start=2):
        nome = str(row.get("nome") or "").strip()
        texto = row.get("texto")
        formato = str(row.get("formato") or "").strip()
        if not nome:
            raise _fail("CONFIG_INVALID", "linha %d sem nome" % numero,
                        linha=numero)
        if formato not in matriz:
            raise _fail("FORMAT_UNSUPPORTED", "formato fora da matriz: %r" % formato,
                        linha=numero, formato=formato)
        chave = slug(nome)
        if not chave:
            raise _fail("CONFIG_INVALID",
                        "linha %d sem slug valido" % numero, linha=numero)
        if chave in vistos:
            raise _fail("NAME_COLLISION", "nomes %r e %r geram o mesmo slug %r"
                        % (vistos[chave], nome, chave), slug=chave, linha=numero)
        vistos[chave] = nome
        item = {"slug": chave, "nome": nome, "formato": formato,
                "texto": "" if texto is None else str(texto)}
        for campo, valor in row.items():
            campo = str(campo).strip().lower()
            if campo and campo not in item and campo not in _COLUNAS:
                item[campo] = valor
        plano.append(item)
    return plano


def _escrever_json(path: Path, data) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    except OSError as exc:
        raise _fail("CONFIG_INVALID", "saida ilegivel: %s" % path,
                    path=str(path), error=str(exc)) from exc


def run_validate_data(src, out, formatos=None) -> dict:
    """Valida a entrada e grava `out` com o plano de artes do lote."""
    origem = _path(src, "entrada")
    destino = _path(out, "saida")
    linhas = _ler_linhas(origem)
    matriz = _matriz(formatos)
    if len(linhas) > MAX_LINHAS:
        raise _fail("LOTE_TOO_BIG", "lote com %d linhas (limite %d)"
                    % (len(linhas), MAX_LINHAS), linhas=len(linhas))
    total = len(linhas) * len(matriz)
    if total > MAX_ARQUIVOS:
        raise _fail("LOTE_TOO_BIG", "lote com %d arquivos (limite %d)"
                    % (total, MAX_ARQUIVOS), linhas=len(linhas), formatos=len(matriz))
    plano = _plano(linhas, matriz)
    _escrever_json(destino, plano)
    return {"linhas": len(plano), "arquivos": total, "plan": str(destino)}
