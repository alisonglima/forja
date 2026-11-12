"""Verificador de grafia da marca LEO (contrato T-GRAFIA-01).

Le as regras de `verificacao` do `grafia.json` da marca e devolve achados
no formato `{"level", "code", "msg", "trecho"}`. Regex case-sensitive.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_BRAND_PADRAO = Path(__file__).resolve().parents[1] / "brands" / "leo-lions"


def _regras(root: Path) -> list[tuple[str, str, re.Pattern, str]]:
    """Carrega as regras de reprova e avisa do brand_root."""
    dados = json.loads((Path(root) / "grafia.json").read_text(encoding="utf-8"))
    ver = dados.get("verificacao") or {}
    out = []
    for level, chave in (("error", "reprova"), ("warn", "avisa")):
        for item in ver.get(chave) or []:
            out.append((level, item["codigo"], re.compile(item["padrao"]),
                        item.get("mensagem", "")))
    return out


def check_text(texto, idioma: str = "pt-BR", brand_root=None) -> list[dict]:
    """Devolve os achados de grafia no texto (vazio se nao se aplica)."""
    if idioma != "pt-BR" or not isinstance(texto, str) or not texto:
        return []
    texto = texto.replace("\u2019", "'")
    root = _BRAND_PADRAO if brand_root is None else Path(brand_root)
    try:
        regras = _regras(root)
    except (OSError, ValueError, KeyError, TypeError):
        return []
    achados = []
    for level, code, rx, msg in regras:
        for match in rx.finditer(texto):
            achados.append({"level": level, "code": code, "msg": msg,
                            "trecho": match.group(0)})
    return achados
