"""Contrato da prova (d): lote CSV de 3 linhas em p5-04-lote/ (plano:2280-2303).
Congela o CSV RFC4180 com a 3a linha quebrada em "nome" (plano:2282-2290), o
PDF de 3 páginas com "João Conceição" acentuado, "Ana"/"Paula" em linhas
separadas na mesma página e o nome longo inteiro ou overflow na linha 1
(plano:2303); 3 PNGs únicos por slug, nenhuma linha perdida (plano:2303).
A árvore é a de plano:2356; o teste é o contrato, o .mjs/.sh só grava (plano:2347).
# LACUNA: o plano não fixa o log de preflight, a regra de slug, hash por
# artefato nem 1 PDF vs 3 PDFs; aceito *.log, slug ASCII, sha256 e páginas totais (plano:2399).
# DIVERGENCIA: plano:2298 grava lote.pdfinfo.txt; a árvore de plano:2356 o omite.
"""
from __future__ import annotations
import csv, hashlib, io, json, os, re
from pathlib import Path
import pytest
RAIZ = Path(__file__).resolve().parents[2]
EVID = RAIZ / ".work/prova-kit/evidencias/p5-04-lote"
CAB = ["nome", "cargo", "titulo"]
LINHAS = [
    ("Maria Aparecida de Oliveira Santos Nascimento", "Coordenação", "Encontro de líderes"),
    ("João Conceição", "Educação", "Ação de formação"),
    ("Ana\nPaula", "Voluntariado", "Café com a comunidade"),
]
LONGO = LINHAS[0][0]
SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]*\.png$")
HEX = re.compile(r"^[0-9a-f]{64}$")
def _paginas(t):
    return [p for p in t.split("\f") if p.strip()]
def _quebra(ps):
    return any({"Ana", "Paula"} <= {l.strip() for l in p.splitlines()} for p in ps)
def _ler(base):
    ev = {"presentes": sorted(p.name for p in base.iterdir())}
    for k, n in (("lote_csv", "lote.csv"), ("arquivos", "arquivos.txt"),
                 ("pdftotext", "lote.pdftotext.txt"), ("erro_json", "erro.json")):
        f = base / n
        ev[k] = f.read_text("utf-8") if f.is_file() else None
    sha = {}
    somas = base / "sha256sums.txt"
    if somas.is_file():
        for linha in somas.read_text("utf-8").splitlines():
            q = linha.split()
            if len(q) == 2 and HEX.match(q[0].lower()):
                sha[q[1].lstrip("*")] = q[0].lower()
    else:
        sha = {n: hashlib.sha256((base / n).read_bytes()).hexdigest()
               for n in ev["presentes"] if (base / n).is_file()}
    ev["sha256"] = sha
    ev["preflight"] = "\n".join(f.read_text("utf-8") for f in sorted(base.glob("*.log")))
    return ev
def validar(ev):
    """Devolve a lista de problemas da evidência; [] significa contrato cumprido."""
    if isinstance(ev, (str, Path)):
        base = Path(ev)
        if not base.is_dir():
            return [f"diretório de evidência ausente: {base}"]
        ev = _ler(base)
    if not isinstance(ev, dict):
        return ["evidência deve ser dict ou caminho de diretório"]
    p = []
    for k, n in (("lote_csv", "lote.csv"), ("arquivos", "arquivos.txt"),
                 ("pdftotext", "lote.pdftotext.txt")):
        if not ev.get(k):
            p.append(f"arquivo ausente ou vazio: {n}")
    b = ev.get("lote_csv") or ""
    if b:
        try:
            rows = list(csv.reader(io.StringIO(b)))
        except csv.Error:
            rows = []
            p.append("lote.csv não é CSV RFC4180")
        if not rows or rows[0] != CAB or len(rows) != 4 or [tuple(x) for x in rows[1:]] != LINHAS:
            p.append("lote.csv: cabeçalho, 3 linhas, valores/acentos ou quebra divergem")
    t = ev.get("pdftotext") or ""
    if t:
        ps = _paginas(t)
        if len(ps) != 3:
            p.append(f"PDF com {len(ps)} páginas (esperado 3)")
        if "João Conceição" not in t or "Conceição" not in t:
            p.append("pdftotext sem 'João Conceição'/'Conceição' acentuados")
        if not _quebra(ps):
            p.append("'Ana' e 'Paula' não estão em linhas separadas na mesma página")
        if not any(LONGO in re.sub(r"\s+", " ", pag) for pag in ps):
            pf = re.sub(r"\s+", " ", ev.get("preflight") or "")
            if not ("overflow" in pf.lower() and "Maria Aparecida" in pf
                    and re.search(r"(linha|line)\s*1\b", pf, re.I)):
                p.append("nome longo truncado sem overflow na linha 1 do preflight")
    nomes = [x.strip() for x in (ev.get("arquivos") or "").splitlines() if x.strip()]
    pngs = [x for x in nomes if x.lower().endswith(".png")]
    pdfs = [x for x in nomes if x.lower().endswith(".pdf")]
    if len(pngs) != 3 or len(set(pngs)) != 3:
        p.append(f"PNGs: {len(pngs)} arquivos, {len(set(pngs))} nomes únicos (esperado 3/3)")
    p += [f"PNG fora do slug ASCII minúsculo: {n}" for n in pngs if not SLUG.match(n)]
    if not pdfs:
        p.append("arquivos.txt não lista PDF")
    faltam = [x for x in nomes if x not in (ev.get("presentes") or nomes)]
    if faltam:
        p.append(f"arquivo listado ausente no diretório: {faltam[0]}")
    sha = ev.get("sha256") or {}
    req = ["lote.csv", "lote.pdftotext.txt", "arquivos.txt"] + pdfs + pngs
    p += [f"hash ausente: {n}" for n in req if not sha.get(n)]
    p += [f"hash inválido: {n}" for n in req if sha.get(n) and not HEX.match(str(sha[n]).lower())]
    erro = ev.get("erro_json")
    if erro is not None:
        try:
            registro = json.loads(erro)
        except (TypeError, ValueError):
            p.append("erro.json truncado ou vazio")
        else:
            p.append("erro.json vazio" if not registro else "erro.json presente: a prova falhou")
    return p
def _amostra():
    buf = io.StringIO()
    csv.writer(buf).writerows([CAB] + [list(x) for x in LINHAS])
    pngs = ["maria-aparecida-de-oliveira-santos-nascimento.png",
            "joao-conceicao.png", "ana-paula.png"]
    nomes = pngs + ["lote.pdf"]
    texto = ("Maria Aparecida de Oliveira\nSantos Nascimento\nJoão Conceição\n"
             "Ana\nPaula\n\fJoão Conceição\n\fCafé com a comunidade\n\f")
    sha = {n: "a" * 64 for n in ["lote.csv", "lote.pdftotext.txt", "arquivos.txt"] + nomes}
    return {"lote_csv": buf.getvalue(), "arquivos": "\n".join(nomes) + "\n",
            "pdftotext": texto, "preflight": "", "sha256": sha, "presentes": nomes}
def test_contrato_evidencia_valida():
    assert validar(_amostra()) == []
def test_contrato_arquivo_ausente():
    ev = _amostra(); ev.pop("lote_csv")
    assert any("lote.csv" in x for x in validar(ev))
def test_contrato_valor_fora_do_criterio():
    ev = _amostra(); ev["pdftotext"] = "João Conceição\n\fAna\nPaula\n\f"
    assert any("páginas" in x for x in validar(ev))
@pytest.mark.parametrize("bruto", ["{", ""])
def test_contrato_json_truncado_ou_vazio(bruto):
    ev = _amostra(); ev["erro_json"] = bruto
    assert any("erro.json" in x for x in validar(ev))
def test_contrato_hash_ausente():
    ev = _amostra(); del ev["sha256"]["lote.csv"]
    assert any("hash ausente: lote.csv" in x for x in validar(ev))
def test_evidencia_real():
    if os.environ.get("FORJA_PROVA_KIT") != "1":
        pytest.skip("defina FORJA_PROVA_KIT=1 com .work/prova-kit/evidencias/p5-04-lote/")
    problemas = validar(EVID)
    assert problemas == [], f"p5-04-lote: {'; '.join(problemas)}"
