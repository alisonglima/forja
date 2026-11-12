"""Renderiza o plano do lote-digital, um arquivo por linha.

O exportador e injetavel: `export(slug, formato, destino)` grava o arquivo
no caminho pedido. Sem injecao, delega ao kit fixo (`forja.kit.export`) a
partir do HTML indicado na linha do plano.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from forja import kit
from forja.errors import ForjaError

_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
_PDF = ("pdf", "a4", "a5")


def _fail(code, msg, **details):
    return ForjaError(code, msg, details=details or None)


def _load(plano) -> list:
    """Le o plano JSON; lista nao vazia de linhas."""
    path = Path(plano)
    if not path.is_file():
        raise _fail("MISSING_INPUT", f"plano do lote ausente: {path}",
                    path=str(path))
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _fail("MISSING_INPUT", f"plano do lote ilegivel: {path}",
                    path=str(path), error=str(exc)) from exc
    if not isinstance(dados, list) or not dados:
        raise _fail("MISSING_INPUT",
                    "plano do lote deve ser uma lista nao vazia", path=str(path))
    return dados


def _campos(item, pos) -> tuple[str, str]:
    """Valida slug e formato de uma linha do plano."""
    if not isinstance(item, dict):
        raise _fail("MISSING_INPUT", f"linha {pos} do plano nao e objeto")
    slug, formato = item.get("slug"), item.get("formato")
    if not isinstance(slug, str) or not _SLUG.match(slug):
        raise _fail("CONFIG_INVALID", f"slug invalido na linha {pos}",
                    slug=slug)
    if not isinstance(formato, str) or not formato.strip():
        raise _fail("CONFIG_INVALID", f"formato ausente na linha {pos}",
                    slug=slug)
    return slug, formato.strip()


def _ext(formato: str) -> str:
    """Extensao de saida: PDF para a familia A4/A5, PNG no resto."""
    base = formato.strip().lower()
    return "pdf" if base.startswith("pdf") or base in _PDF else "png"


def _export_kit(item, formato, destino) -> None:
    """Adapter do kit: exporta o HTML da linha e copia a primeira saida."""
    alvo = (item.get("html") or item.get("template")
            or item.get("arquivo") or item["slug"])
    resultado = kit.export(alvo, variant=item.get("variant"))
    saidas = [str(p) for p in (resultado.get("outputs") or []) if str(p).strip()]
    if not saidas:
        raise _fail("PROVIDER_ERROR", "kit export nao devolveu arquivo",
                    slug=item.get("slug"))
    shutil.copyfile(saidas[0], destino)


def run_render_lote(plano, destino, *, export=None) -> list[str]:
    """Renderiza cada linha do plano e devolve os slugs na ordem do plano."""
    itens = _load(plano)
    raiz = Path(destino)
    raiz.mkdir(parents=True, exist_ok=True)
    artes, vistos = [], set()
    for pos, item in enumerate(itens):
        slug, formato = _campos(item, pos)
        if slug in vistos:
            raise _fail("NAME_COLLISION", f"slug repetido no plano: {slug}",
                        slug=slug)
        vistos.add(slug)
        alvo = raiz / f"{slug}.{_ext(formato)}"
        tmp = alvo.with_name(alvo.name + ".part")
        try:
            if export is None:
                _export_kit(item, formato, tmp)
            else:
                export(slug, formato, tmp)
        except ForjaError:
            tmp.unlink(missing_ok=True)
            raise
        except (FileNotFoundError, ModuleNotFoundError) as exc:
            tmp.unlink(missing_ok=True)
            raise _fail("MISSING_PREREQ",
                        f"pre-requisito ausente ao renderizar {slug}: {exc}",
                        slug=slug, error=str(exc)) from exc
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            raise _fail("PROVIDER_ERROR",
                        f"falha ao renderizar {slug}: {exc}",
                        slug=slug, error=str(exc)) from exc
        if not tmp.is_file():
            raise _fail("PROVIDER_ERROR",
                        f"export nao gerou arquivo para {slug}", slug=slug,
                        path=str(alvo))
        tmp.replace(alvo)
        artes.append(slug)
    return artes
