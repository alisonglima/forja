"""Contrato da prova de aprovação visual humana (K.4; plano:2406-2430).
Congela `aprovacao-visual/<peca>.json` com arquivo, sha256, capturas
[1280, 360], aberto_em, por, decisao e notas; `decisao=aprovado`; sha256
igual ao do arquivo, então arte nova invalida. `validar(ev)` recebe dict ou
caminho JSON e devolve problemas ([] ok); a evidência real só roda com
FORJA_PROVA_KIT=1. O .mjs/.sh nunca é o contrato (plano:2345-2405).
# DIVERGENCIA: story em 720/360 (plano:2408-2410) vs. resumo 1280/360: aceito ambos.
# LACUNA: tipo de `capturas`/formato de `aberto_em`; `arquivo` relativo usa a raiz.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

CAMPOS = ("arquivo", "sha256", "capturas", "aberto_em", "por", "decisao", "notas")


def _sha(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _carregar(ev):
    """Devolve (evidência, raiz, problema); não levanta exceção."""
    if isinstance(ev, dict):
        return dict(ev), Path.cwd(), None
    caminho = Path(ev)
    if not caminho.is_file():
        return None, None, f"arquivo de evidência ausente: {caminho}"
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, None, f"JSON truncado/vazio em {caminho}: {exc}"
    if not isinstance(dados, dict):
        return None, None, f"{caminho} não contém um objeto JSON"
    return dados, caminho.parent.parent, None


def validar(ev):
    """Valida um registro de aprovação visual; devolve lista de problemas."""
    ev, raiz, problema = _carregar(ev)
    if problema:
        return [problema]
    problemas = [f"campo obrigatório ausente: {c}" for c in CAMPOS if c not in ev]
    if problemas:
        return problemas
    if ev["decisao"] != "aprovado":
        problemas.append(f"decisao deve ser 'aprovado' (valor: {ev['decisao']!r})")
    if not isinstance(ev["por"], str) or not ev["por"].strip():
        problemas.append("por deve ser texto não vazio")
    if not isinstance(ev["notas"], str):
        problemas.append("notas deve ser texto")
    if not isinstance(ev["aberto_em"], str) or not ev["aberto_em"].strip():
        problemas.append("aberto_em deve ser texto não vazio")
    capturas = ev["capturas"]
    if not isinstance(capturas, list) or not all(isinstance(n, int) for n in capturas):
        problemas.append("capturas deve ser lista de inteiros (maior lado em px)")
    elif capturas not in ([1280, 360], [720, 360]):  # story: 720x1280/360x640
        problemas.append(f"capturas fora do critério 1280/360: {capturas}")
    registro = ev["sha256"]
    if not isinstance(registro, str) or len(registro) != 64 or registro.strip("0123456789abcdefABCDEF"):
        problemas.append("sha256 ausente ou inválido (esperado 64 hex)")
    else:
        arquivo = Path(ev["arquivo"])
        if not arquivo.is_absolute():
            arquivo = raiz / arquivo
        if not arquivo.is_file():
            problemas.append(f"arquivo ausente: {arquivo}")
        elif _sha(arquivo) != registro.lower():
            problemas.append("sha256 não confere com o arquivo; arte nova invalida")
    return problemas


def _amostra(tmp_path: Path, **mudancas) -> dict:
    arte = tmp_path / "peca.txt"
    arte.write_text("arte v1", encoding="utf-8")
    ev = {"arquivo": str(arte), "sha256": _sha(arte), "capturas": [1280, 360],
          "aberto_em": "2026-11-11T10:00:00-03:00", "por": "humano",
          "decisao": "aprovado", "notas": ""}
    ev.update(mudancas)
    return ev


def test_validar_contrato_amostra_valida(tmp_path):
    assert validar(_amostra(tmp_path)) == []


def test_validar_contrato_arquivo_ausente(tmp_path):
    assert any("arquivo ausente" in p for p in validar(_amostra(tmp_path, arquivo="/x")))


@pytest.mark.parametrize(("mudanca", "trecho"),
    [({"decisao": "pendente"}, "decisao"), ({"capturas": [1280]}, "capturas"),
     ({"sha256": None}, "sha256"), ({"sha256": "0" * 64}, "não confere")])
def test_validar_contrato_valor_fora_do_criterio(tmp_path, mudanca, trecho):
    assert any(trecho in p for p in validar(_amostra(tmp_path, **mudanca)))


def test_validar_contrato_json_truncado_ou_vazio(tmp_path):
    for conteudo in ("", '{"arquivo":'):
        caminho = tmp_path / "aprovacao-visual" / "cartao.json"
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
        assert any("JSON" in p for p in validar(caminho))


def test_evidencia_real():
    if os.environ.get("FORJA_PROVA_KIT") != "1":
        pytest.skip("defina FORJA_PROVA_KIT=1 após a aprovação humana")
    pasta = Path(__file__).resolve().parents[2] / ".work/prova-kit/evidencias/aprovacao-visual"
    registros = sorted(pasta.glob("*.json")) if pasta.is_dir() else []
    if not registros:
        pytest.fail(f"evidência ausente ou sem registro: {pasta}")
    for caminho in registros:
        problemas = validar(caminho)
        assert not problemas, f"{caminho}: {problemas}"
