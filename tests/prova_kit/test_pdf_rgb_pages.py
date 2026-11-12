"""Contrato da prova (b), parte 2: folder multipágina em `p5-02-pdf/`.

Congela 4 páginas A5 419,5x595,3 pt ±0,5 e `folder-paginas.txt` com
texto selecionável por página (plano:2257, 2253-2254), na árvore
`p5-02-pdf/` (plano:2354). Quem julga é este teste, não o script
(plano:2347); evidência real só com `FORJA_PROVA_KIT=1`, senão skip.
"""

from __future__ import annotations

import hashlib, json, os, re
from pathlib import Path

import pytest

# DIVERGENCIA: comando grava em `p5-02/` (plano:2246-2254); árvore canônica é `p5-02-pdf/` (plano:2354).
# DIVERGENCIA: `pdfinfo` sem -f/-l (plano:2246) só mede a 1ª página; "cada página A5" (plano:2257) exige `Page N size`.
# LACUNA: plano não enumera os quatro títulos; exijo texto alfabético por página. K.3 não lista hash; exijo sha256.
EVIDENCIAS = Path(__file__).resolve().parents[2] / ".work" / "prova-kit" / "evidencias" / "p5-02-pdf"
A5, TOL = (419.5, 595.3), 0.5

def _ler(ev):
    """Aceita dict sintético, diretório de evidência ou JSON serializado."""
    if isinstance(ev, dict):
        return ev, []
    caminho = Path(ev)
    if not caminho.exists():
        return None, [f"evidência ausente: {caminho}"]
    if caminho.is_file():
        texto = caminho.read_text(encoding="utf-8", errors="replace").strip()
        if not texto:
            return None, [f"JSON vazio: {caminho}"]
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError as exc:
            return None, [f"JSON truncado/inválido: {exc}"]
        return (dados, []) if isinstance(dados, dict) else (None, [f"JSON não é objeto: {caminho}"])
    pdf = caminho / "folder.pdf"
    dados = {"pdf": str(pdf) if pdf.is_file() else None, "pdfinfo": None, "paginas_txt": None}
    if pdf.is_file():
        dados["sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    for chave, nome in (("pdfinfo", "folder.pdfinfo.txt"), ("paginas_txt", "folder-paginas.txt")):
        alvo = caminho / nome
        if alvo.is_file():
            dados[chave] = alvo.read_text(encoding="utf-8", errors="replace")
    return dados, []

def validar(ev):
    """Devolve os problemas da evidência do folder; lista vazia = passou."""
    dados, problemas = _ler(ev)
    if dados is None:
        return problemas
    for chave, rotulo in (("pdf", "folder.pdf"), ("pdfinfo", "folder.pdfinfo.txt"), ("paginas_txt", "folder-paginas.txt")):
        if not dados.get(chave):
            problemas.append(f"arquivo ausente ou vazio: {rotulo}")
    info = dados.get("pdfinfo") or ""
    m = re.search(r"^Pages:\s*(\d+)\s*$", info, re.M)
    n = int(m.group(1)) if m else 0
    if n != 4:
        problemas.append(f"folder com {n} página(s); critério: 4 (plano:2257)")
    tamanhos = re.findall(r"^Page\s+(\d+)\s+size:\s*([\d.,]+)\s*x\s*([\d.,]+)\s*pt", info, re.M)
    if len(tamanhos) != 4:
        problemas.append(f"pdfinfo traz {len(tamanhos)} tamanho(s); faltam as 4 A5 (plano:2257)")
    for numero, largura, altura in tamanhos:
        w, h = (float(v.replace(",", ".")) for v in (largura, altura))
        if abs(w - A5[0]) > TOL or abs(h - A5[1]) > TOL:
            problemas.append(f"página {numero} com {w}x{h} pt; A5 esperado 419,5x595,3 ±0,5")
    paginas = [p for p in (dados.get("paginas_txt") or "").split("\f") if p.strip()]
    if len(paginas) != 4:
        problemas.append(f"folder-paginas.txt traz {len(paginas)} página(s); critério: 4 (plano:2253-2254)")
    for numero, pagina in enumerate(paginas, 1):
        if not any(c.isalpha() for c in pagina):
            problemas.append(f"página {numero} sem texto selecionável (plano:2257)")
    digest = str(dados.get("sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        problemas.append("hash ausente ou inválido: sha256 do folder.pdf")
    return problemas

def _info(paginas=4, tamanho="419.528 x 595.276"):
    return f"Pages:           {paginas}\n" + "\n".join(f"Page    {n} size:  {tamanho} pts" for n in range(1, 5)) + "\n"

def _ev_ok(**mudancas):
    ev = {"pdf": "folder.pdf", "pdfinfo": _info(), "paginas_txt": "Capa\fBoas-vindas\fProgramação\fContato\f", "sha256": "0" * 64}
    return {**ev, **mudancas}

def test_contrato_amostra_valida(tmp_path):
    pasta = tmp_path / "p5-02-pdf"; pasta.mkdir()
    (pasta / "folder.pdf").write_bytes(b"%PDF-1.4\n")
    (pasta / "folder.pdfinfo.txt").write_text(_info(), encoding="utf-8")
    (pasta / "folder-paginas.txt").write_text(_ev_ok()["paginas_txt"], encoding="utf-8")
    assert validar(_ev_ok()) == [] and validar(pasta) == []

def test_contrato_arquivo_ausente(tmp_path):
    pasta = tmp_path / "p5-02-pdf"; pasta.mkdir()
    (pasta / "folder.pdfinfo.txt").write_text(_info(), encoding="utf-8")
    assert any("folder.pdf" in p for p in validar(pasta))

def test_contrato_valor_fora_do_criterio():
    assert any("critério: 4" in p for p in validar(_ev_ok(pdfinfo=_info(3))))
    assert any("A5 esperado" in p for p in validar(_ev_ok(pdfinfo=_info(tamanho="500 x 595.276"))))

def test_contrato_pagina_sem_texto():
    assert any("sem texto selecionável" in p for p in validar(_ev_ok(paginas_txt="Capa\f123\fProgramação\fContato\f")))

def test_contrato_json_truncado_ou_vazio(tmp_path):
    for i, conteudo in enumerate(('{"pdf": "folder.pdf",', "")):
        alvo = tmp_path / f"ev{i}.json"; alvo.write_text(conteudo, encoding="utf-8")
        assert any(("truncado" in p) or ("vazio" in p) for p in validar(alvo))

def test_contrato_hash_ausente():
    ev = _ev_ok(); del ev["sha256"]
    assert any("hash ausente" in p for p in validar(ev))

def test_evidencia_real():
    if os.environ.get("FORJA_PROVA_KIT") != "1":
        pytest.skip("defina FORJA_PROVA_KIT=1 para ler a evidência real")
    assert validar(EVIDENCIAS) == [], EVIDENCIAS
