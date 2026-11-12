"""Contrato de dado do PPTX (T-PPTX-01; plano:1647-1753, 1885-1917, 2052-2061).
Congela: deck.yaml/forja-deck/v1 (plano:1647-1700), os 12 modelos, limites e formas
(plano:1704-1723), o catalogo forja-deck-models/v2 com 1 base + 3 fontes opcionais
(plano:1725-1753, 2052-2061) e a abertura do .pptx so para ler (plano:1753).
LACUNA: o plano nao fixa quantos slides nem quais modelos o modelo.yaml de exemplo tem,
nem os nomes das chaves de limits fora de titulo/subtitulo/corpo.
LACUNA: locale/modelo_catalogo aparecem no exemplo, mas nao na tabela de campos do deck.
LACUNA: nao ha lista de chaves permitidas por modelo em slides[]; so tipo/conteudo e checado.
"""
import hashlib, json, os, posixpath, re, zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
import pytest, yaml

RAIZ = Path(__file__).resolve().parents[1]
DECKS = RAIZ / "brands" / "leo-lions" / "decks"
CATALOGO, MODELO = DECKS / "modelos.json", DECKS / "modelo.yaml"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
TEMPLATES = {
    "lions-oficial-2022": ("base", False, True, "box/C-apresentacoes/LI_BrandResources_Template_PPT_13.3x7.5_Presentation_00a.pptx", "4a5b521de577453a7e50065a2a1fc5d658879ccde37267a1e8a56ad84f6f9d24", 18518334, 115, 3, 30, ["lions", "leo-lion"]),
    "mission-brief-2026": ("slide-source", True, False, "site-extra/resources/152441463__Mission Brief Presentation_en.pptx", "07e0302a650c2c0028c2e31f370ef1a9a4248424219c0c83d00314fc42b3e9fc", 66852075, 32, 2, 0, ["lions"]),
    "service-journey-2026": ("slide-source", True, False, "site-extra/resources/122465944__ContinuingtheServiceJourney_en.pptx", "155a5452e0533d5113cf4594576df65436f4196bf7c6d472328ff18a73b3960f", 22297824, 26, 2, 0, ["lions"]),
    "new-club-development-2026": ("slide-source", True, False, "site-extra/resources/97013210__New Club Development WorkshopTraining_en.pptx", "62ce24a3240c274d8a3275a3912bcee6953c5d1908e0cda67508da644677d313", 138849830, 88, 3, 0, ["lions"]),
}
MODELOS = {
    "capa_foto": (2, "L26", ["Headline", "Subhead", "Picture 1"]),
    "secao": (7, "L26", ["Text Placeholder 1"]),
    "texto": (16, "L26", ["Large #", "Body Copy"]),
    "imagem_texto": (48, "L26", ["Body Copy", "Body Copy", "Background - Image"]),
    "citacao": (60, "L26", ["Body Copy", "Quote"]),
    "numeros": (84, "L26", ["TextBox 6", "TextBox 3", "TextBox 8", "TextBox 9", "TextBox 10"]),
    "grafico": (76, "L26", ["Headline", "Chart 2"]),
    "agenda": (31, "L26", ["Text Placeholder 18", "TextBox 138"]),
    "tabela": (59, "L26", ["Table 7"]),
    "equipe": (64, "L25", ["Rectangle 25"]),
    "contato": (57, "L26", ["Headline"]),
    "fechamento": (70, "L26", ["Title 1", "TextBox 7"]),
}
TITULOS = {"capa_foto": (8, 48), "secao": (6, 40), "texto": (8, 48), "imagem_texto": (8, None),
           "grafico": (8, None), "agenda": (6, None), "fechamento": (6, None)}

def _catalogo():
    assert CATALOGO.is_file(), CATALOGO
    return json.loads(CATALOGO.read_text(encoding="utf-8"))
def _modelo():
    assert MODELO.is_file(), MODELO
    return yaml.safe_load(MODELO.read_text(encoding="utf-8"))
def _acervo():
    if os.environ.get("FORJA_BRAND_SOURCES"):
        return Path(os.environ["FORJA_BRAND_SOURCES"])
    base = next((p for p in Path(__file__).resolve().parents if (p / ".work/fontes/lions").is_dir()), None)
    return base / ".work/fontes/lions" if base else None
def _exige_acervo():
    raiz = _acervo()
    if raiz is None:
        pytest.skip("acervo ausente: defina FORJA_BRAND_SOURCES")
    return raiz
def _sha256(caminho):
    h = hashlib.sha256()
    with caminho.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()
def _nomes(shapes):
    return [s if isinstance(s, str) else s.get("name") or s.get("nome") or next(iter(s))
            for s in shapes]
def _formas(caminho, numeros):
    with zipfile.ZipFile(caminho) as z:
        pres = ET.fromstring(z.read("ppt/presentation.xml"))
        rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))}
        ordem = [posixpath.normpath(posixpath.join("ppt", rels[s.get(R + "id")])) for s in pres.iter(P + "sldId")]
        nomes = {n: Counter(e.get("name") for e in ET.fromstring(z.read(ordem[n - 1])).iter()
                           if e.tag.endswith("}cNvPr") and e.get("name")) for n in set(numeros)}
        masters = len([n for n in z.namelist() if re.fullmatch(r"ppt/slideMasters/slideMaster\d+\.xml", n)])
        layouts = len([n for n in z.namelist() if re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", n)])
    return nomes, masters, layouts
def _texto(valor):
    if isinstance(valor, list):
        assert valor and all(isinstance(x, str) and x.strip() for x in valor)
        return " ".join(valor)
    assert isinstance(valor, str) and valor.strip()
    return valor

def test_catalogo_schema_v2_e_quatro_templates():
    c = _catalogo()
    assert (c["schema"], c["brand"], c["default_template_id"]) == ("forja-deck-models/v2", "leo-lions", "lions-oficial-2022")
    assert len(c["templates"]) == 4 and {t["template_id"] for t in c["templates"]} == set(TEMPLATES)
    base = [t for t in c["templates"] if t["role"] == "base"]
    fontes = [t for t in c["templates"] if t["role"] == "slide-source"]
    assert len(base) == 1 and base[0]["template_id"] == c["default_template_id"]
    assert (base[0]["optional"], base[0]["compose"]) == (False, True)
    assert len(fontes) == 3 and all(t["optional"] is True and t["compose"] is False for t in fontes)
    por_id = {t["template_id"]: t for t in c["templates"]}
    for tid, meta in TEMPLATES.items():
        t = por_id[tid]
        assert (t["role"], t["optional"], t["compose"], t["file"], t["sha256"], t["bytes"],
                t["slides"], t["masters"], t["layouts"]) == meta[:9]
        assert set(t["variants"]) == set(meta[9])
        assert re.fullmatch(r"[0-9a-f]{64}", t["sha256"])
        assert not Path(t["file"]).is_absolute() and ".." not in Path(t["file"]).parts

def test_catalogo_doze_modelos_fechados_com_slides_layouts_e_formas():
    modelos = _catalogo()["models"]
    assert set(modelos) == set(MODELOS)
    for nome, (slide, layout, formas) in MODELOS.items():
        entrada = modelos[nome]
        assert (entrada["slide"], entrada["layout"]) == (slide, layout)
        assert Counter(_nomes(entrada["shapes"])) == Counter(formas)

def test_catalogo_limites_do_contrato():
    modelos = _catalogo()["models"]
    assert modelos["capa_foto"]["limits"]["titulo"] == modelos["texto"]["limits"]["titulo"] == {"palavras": 8, "chars": 48}
    assert modelos["capa_foto"]["limits"]["subtitulo"] == {"palavras": 12, "chars": 80}
    assert modelos["texto"]["limits"]["corpo"] == {"chars": 180}
    for nome, (palavras, chars) in TITULOS.items():
        limite = modelos[nome]["limits"]["titulo"]
        assert limite["palavras"] == palavras and (chars is None or limite["chars"] == chars)
    assert modelos["imagem_texto"]["limits"]["corpo"]["chars"] == 220
    assert all(isinstance(m["limits"], dict) and m["limits"] for m in modelos.values())

def test_catalogo_sha256_bate_com_os_arquivos_do_acervo():
    raiz = _exige_acervo()
    por_id = {t["template_id"]: t for t in _catalogo()["templates"]}
    for tid, meta in TEMPLATES.items():
        t = por_id[tid]
        caminho = raiz / t["file"]
        assert caminho.is_file(), (tid, t["file"])
        assert caminho.stat().st_size == t["bytes"]
        assert _sha256(caminho) == t["sha256"]

def test_catalogo_formas_existem_nos_slides_de_origem():
    raiz = _exige_acervo()
    base = {t["template_id"]: t for t in _catalogo()["templates"]}["lions-oficial-2022"]
    por_slide, masters, layouts = _formas(raiz / base["file"], [v[0] for v in MODELOS.values()])
    assert (masters, layouts) == (3, 30)
    for nome, (numero, _layout, formas) in MODELOS.items():
        assert Counter(formas) - por_slide[numero] == Counter(), (nome, por_slide[numero])

def test_modelo_yaml_v1_e_deck_do_template_base():
    m = _modelo()
    assert set(m) == {"schema", "deck", "slides"} and m["schema"] == "forja-deck/v1"
    d = m["deck"]
    assert set(d) == {"template", "template_sha256", "brand", "variant", "size", "locale", "notas", "modelo_catalogo"}
    assert d["template"] == "lions-oficial-2022"
    assert d["template_sha256"] == TEMPLATES["lions-oficial-2022"][4]
    assert d["brand"] == "leo-lions" and d["variant"] in {"lions", "leo", "leo-lion"}
    assert d["size"] == "13.333x7.5in" and d["locale"] == "pt-BR"
    assert isinstance(d["notas"], bool) and d["modelo_catalogo"] == "brands/leo-lions/decks/modelos.json"

def test_modelo_slides_fechados_dentro_dos_limites_e_tipos():
    slides = _modelo()["slides"]
    assert isinstance(slides, list) and 3 <= len(slides) <= 40
    for s in slides:
        assert isinstance(s, dict) and isinstance(s.get("modelo"), str) and s["modelo"] in MODELOS
        assert set(s) - {"modelo", "notas", "imagem", "imagem_sha256"}, "slide sem conteudo"
        for chave in ("titulo", "subtitulo", "numero", "legenda", "rodape", "citacao", "atribuicao", "imagem", "imagem_sha256", "notas"):
            if chave in s:
                assert isinstance(s[chave], str) and s[chave].strip()
        nome = s["modelo"]
        if "titulo" in s and nome in TITULOS:
            texto = _texto(s["titulo"])
            palavras, chars = TITULOS[nome]
            assert len(texto.split()) <= palavras and (chars is None or len(texto) <= chars)
        if nome == "capa_foto" and "subtitulo" in s:
            texto = _texto(s["subtitulo"])
            assert len(texto.split()) <= 12 and len(texto) <= 80
        if "corpo" in s and nome in {"texto", "imagem_texto"}:
            assert len(_texto(s["corpo"])) <= {"texto": 180, "imagem_texto": 220}[nome]

def test_modelo_imagens_sao_relativas_e_tem_sha256():
    for s in _modelo()["slides"]:
        assert ("imagem" in s) == ("imagem_sha256" in s)
        if "imagem" in s:
            caminho = Path(_texto(s["imagem"]))
            assert not caminho.is_absolute() and ".." not in caminho.parts
            assert isinstance(s["imagem_sha256"], str)
            assert re.fullmatch(r"[0-9a-fA-F]{64}", s["imagem_sha256"])
