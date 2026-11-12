"""Contrato da prova (b), parte 1: PDF RGB A5/A4 (plano:2236-2257, 2354).

Congela pdfinfo (Pages: 1; A5 419,5x595,3 pt; A4 595,3x841,9 pt; +/-0,5),
pdffonts (fonte emb=yes/sub=yes, nenhuma emb=no), pdftotext ("Ação",
"Conceição", "Coração"), pdfimages -list (decorativa rgb, sem imagem de
página inteira como conteúdo) e render pdftocairo em PNG sRGB; exit_code 0
e sha256 por arquivo. O `.mjs`/`.sh` só executa e grava (plano:2345-2347);
o folder multipágina fica para a 02B.
"""
import base64, hashlib, json, os, re
from pathlib import Path
import pytest

RAIZ = Path(__file__).resolve().parents[2]
EVIDENCIA = RAIZ / ".work/prova-kit/evidencias/p5-02-pdf"
PECAS = {"a5": (419.5, 595.3), "a4": (595.3, 841.9)}
TOL, TERMOS = 0.5, ("Ação", "Conceição", "Coração")
NOMES = [n for p in PECAS for n in (f"{p}.pdf", f"{p}.pdfinfo.txt", f"{p}.pdffonts.txt",
         f"{p}.pdftotext.txt", f"{p}.pdfimages.txt", f"{p}-page-1.png")]
PNG_OK = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAAAXNSR0IArs4c6QAAAAxJREFUeJxj+M/AAAADAQEAyf6S7wAAAABJRU5ErkJggg==")
# LACUNA: plano:2354 não nomeia manifesto/hash em p5-02-pdf; o defeito
# "hash ausente" (spec da lane) exige prova.json com exit_code e sha256.
# LACUNA: plano:2251 só imprime identify; K.3:2354 não guarda esse texto,
# então sRGB é lido nos chunks do PNG; "página inteira" = >=95% (plano:2257).
# DIVERGENCIA: plano:2246 grava em p5-02/; K.3:2354 fixa p5-02-pdf/ (mais específico).

def _texto(base, nome):
    p = base / nome
    return p.read_text("utf-8", errors="replace") if p.is_file() else ""

def _sha256(p):
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def _png(p):
    d = p.read_bytes()
    if d[:8] != b"\x89PNG\r\n\x1a\n": return "não é PNG"
    if len(d) < 26 or d[12:16] != b"IHDR" or d[25] not in (2, 6): return "não é RGB"
    return "" if any(m in d for m in (b"sRGB", b"iCCP", b"gAMA")) else "sem marca sRGB"

def _manifesto(ev):
    base = Path(ev["base"]) if isinstance(ev, dict) else Path(ev)
    bruto = ev.get("manifesto", base / "prova.json") if isinstance(ev, dict) else base / "prova.json"
    if isinstance(bruto, Path): bruto = bruto.read_text("utf-8") if bruto.is_file() else None
    if bruto is None: return base, None, ["JSON ausente: prova.json"]
    if isinstance(bruto, dict): return base, bruto, []
    if not str(bruto).strip(): return base, None, ["JSON vazio: prova.json"]
    try: dados = json.loads(bruto)
    except (TypeError, ValueError) as e: return base, None, [f"JSON inválido: {e}"]
    return (base, dados, []) if isinstance(dados, dict) else (base, None, ["JSON inválido: raiz não é objeto"])

def _peca(base, peca, w, h):
    p = []
    info = _texto(base, f"{peca}.pdfinfo.txt").replace(",", ".")
    mp = re.search(r"Pages:\s+(\d+)", info)
    mt = re.search(r"Page size:\s+([\d.]+)\s+x\s+([\d.]+)\s+pt", info)
    if not mp or mp.group(1) != "1" or not mt or abs(float(mt.group(1)) - w) > TOL or abs(float(mt.group(2)) - h) > TOL:
        p.append(f"{peca}: Page size/Pages fora do critério")
    fs = [(a.lower(), b.lower()) for a, b, _ in re.findall(
        r"\s(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$", _texto(base, f"{peca}.pdffonts.txt"), re.M)]
    if not any(a == "yes" and b == "yes" for a, b in fs): p.append(f"{peca}: nenhuma fonte emb=yes e sub=yes")
    if any(a == "no" for a, _ in fs): p.append(f"{peca}: fonte com emb=no")
    txt = _texto(base, f"{peca}.pdftotext.txt")
    falta = [t for t in TERMOS if t not in txt]
    if falta: p.append(f"{peca}: pdftotext sem {', '.join(falta)}")
    imgs = []
    for linha in _texto(base, f"{peca}.pdfimages.txt").splitlines():
        q = linha.split()
        if len(q) < 14 or not q[0].isdigit() or q[2] != "image": continue
        try: cheia = float(q[3]) / float(q[12]) >= .95 * w / 72 and float(q[4]) / float(q[13]) >= .95 * h / 72
        except (ValueError, ZeroDivisionError): cheia = False
        imgs.append((q[5], cheia))
    if any(c != "rgb" for c, _ in imgs): p.append(f"{peca}: pdfimages fora de rgb")
    if len(imgs) == 1 and imgs[0][1] and (falta or not fs): p.append(f"{peca}: imagem de página inteira é o conteúdo")
    png = base / f"{peca}-page-1.png"
    erro = _png(png) if png.is_file() else "ausente"
    if erro: p.append(f"{peca}: render {erro}")
    return p

def validar(ev):
    base, man, probs = _manifesto(ev)
    hashes = man.get("sha256") if man else {}
    if man is not None and man.get("exit_code") != 0: probs.append(f"exit_code fora do critério: {man.get('exit_code')!r}")
    if man is not None and (not isinstance(hashes, dict) or not hashes): probs.append("hash ausente: sha256"); hashes = {}
    for nome in NOMES:
        f = base / nome
        if not f.is_file(): probs.append(f"arquivo ausente: {nome}")
        elif hashes and nome not in hashes: probs.append(f"hash ausente: {nome}")
        elif hashes and not re.fullmatch(r"[0-9a-f]{64}", str(hashes[nome])): probs.append(f"hash inválido: {nome}")
        elif hashes and _sha256(f) != hashes[nome]: probs.append(f"hash divergente: {nome}")
    for peca, (w, h) in PECAS.items(): probs += _peca(base, peca, w, h)
    return probs

def _amostra(tmp_path, manifesto=None, sobrepor=None):
    base = tmp_path / "p5-02-pdf"
    base.mkdir(parents=True)
    for peca, (w, h) in PECAS.items():
        for nome, dados in {
            f"{peca}.pdf": b"%PDF-1.4\n",
            f"{peca}.pdfinfo.txt": f"Pages: 1\nPage size: {w} x {h} pts\n".encode(),
            f"{peca}.pdffonts.txt": b"Demo TrueType WinAnsi yes yes yes 5 0\n",
            f"{peca}.pdftotext.txt": "Ação Conceição Coração\n".encode(),
            f"{peca}.pdfimages.txt": b"page num type width height color comp bpc enc interp object ID x-ppi y-ppi size ratio\n",
            f"{peca}-page-1.png": PNG_OK,
        }.items(): (base / nome).write_bytes(dados)
    for nome, dados in (sobrepor or {}).items(): (base / nome).write_bytes(dados)
    sha = {nome: _sha256(base / nome) for nome in NOMES}
    man = {"schema": "prova-kit/pdf-rgb/v1", "exit_code": 0, "sha256": sha} if manifesto is None else manifesto
    (base / "prova.json").write_text(json.dumps(man), encoding="utf-8")
    return base

def test_contrato_amostra_valida(tmp_path):
    assert validar(_amostra(tmp_path)) == []

def test_contrato_arquivo_ausente(tmp_path):
    base = _amostra(tmp_path); (base / "a5.pdffonts.txt").unlink()
    assert any("arquivo ausente: a5.pdffonts.txt" in x for x in validar(base))

def test_contrato_valor_fora_do_criterio(tmp_path):
    base = _amostra(tmp_path, sobrepor={"a5.pdfinfo.txt": b"Pages: 1\nPage size: 430.0 x 595.3 pts\n"})
    assert any("Page size" in x for x in validar(base))

def test_contrato_json_truncado_ou_vazio(tmp_path):
    for i, bruto in enumerate(('{"exit_code": 0', "")):
        assert any("JSON" in x for x in validar({"base": _amostra(tmp_path / f"c{i}"), "manifesto": bruto}))

def test_contrato_hash_ausente(tmp_path):
    base = _amostra(tmp_path, manifesto={"schema": "prova-kit/pdf-rgb/v1", "exit_code": 0})
    assert any("hash ausente" in x for x in validar(base))

def test_contrato_criterios(tmp_path):
    base = _amostra(tmp_path, sobrepor={"a5.pdffonts.txt": b"Demo Type1 WinAnsi no no no 5 0\n",
        "a5.pdftotext.txt": b"Acao Conceicao Coracao\n",
        "a5.pdfimages.txt": b"1 0 image 100 100 cmyk 4 8 jpeg no 12 0 72 72 1K 1%\n",
        "a5-page-1.png": PNG_OK.replace(b"sRGB", b"xxxx")})
    probs = validar(base)
    assert all(any(a in x for x in probs) for a in ("emb=no", "Ação", "fora de rgb", "sRGB"))

def test_evidencia_real():
    if os.environ.get("FORJA_PROVA_KIT") != "1":
        pytest.skip("define FORJA_PROVA_KIT=1")
    probs = validar(EVIDENCIA)
    assert probs == [], "\n".join(probs)
