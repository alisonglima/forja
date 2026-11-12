"""Contrato do índice da biblioteca de fotos (T-PHOTO-INDEX-01).

Congela L-PHOTO-INDEX-01 (`brands/leo-lions/photos-index.json`, NOVO):
plano:1788 — único índice: 145 rasters, causa, sha256, dimensões,
orientação, tem_pessoas; sem binário; .mp4/PDF fora. plano:2065
(6.V.3.5) — 147 arquivos/11 pastas: 145 raster (118 .jpg, 8 .JPG,
18 .tif, 1 .BMP) + 1 .mp4 + ReadMe PDF (introdução); path relativo;
orientation paisagem|retrato|quadrada; tem_pessoas true|false|null
(null = não inspecionada, bloqueia uso). plano:2081 — esta lane é o
contrato; L-PHOTO-INDEX-01 (outro perfil) não altera este arquivo.
plano:2111 (6.V.7) — tem_pessoas nasce null; sem termos declarados;
foto com pessoa exige autorização prévia; confirmação humana por uso.
"""
import json
import re
from pathlib import Path, PurePosixPath

import pytest

INDEX_REL = Path("brands/leo-lions/photos-index.json")
ASSETS_REL = Path("brands/leo-lions/assets-index.json")
ORIENTATIONS = ("paisagem", "retrato", "quadrada")
RASTER_COUNT = {".jpg": 118, ".JPG": 8, ".tif": 18, ".BMP": 1}  # soma 145
REQUIRED = ("path", "causa", "sha256", "width", "height", "orientation",
            "tem_pessoas", "revisado_por", "revisado_em")
BINARY_KEYS = ("data", "blob", "bytes", "base64", "content")
_SHA = re.compile(r"[0-9a-f]{64}")


def _load_index():
    path = Path(__file__).resolve().parents[1] / INDEX_REL
    if not path.is_file():
        pytest.fail(f"ausente: {INDEX_REL} (L-PHOTO-INDEX-01 ainda não existe)")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        pytest.fail(f"{INDEX_REL} inválido (truncado/corrompido?): {exc}")


def _entries(doc):
    # LACUNA: o contrato não fixa o envelope (lista pura ou {"photos": [...]}).
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict) and isinstance(doc.get("photos"), list):
        return doc["photos"]
    pytest.fail(f"{INDEX_REL}: topo deve ser lista ou objeto com 'photos'")


def _check_entry(entry, i):
    # LACUNA: formato de revisado_por/revisado_em não fixado; só presença.
    assert isinstance(entry, dict), f"entrada {i}: objeto esperado"
    for key in REQUIRED:
        assert key in entry, f"entrada {i}: sem {key!r}"
    path = entry["path"]
    assert isinstance(path, str) and path, f"entrada {i}: path vazio"
    assert not PurePosixPath(path).is_absolute(), f"entrada {i}: absoluto {path!r}"
    assert ".." not in PurePosixPath(path).parts, f"entrada {i}: '..' em {path!r}"
    assert "\\" not in path, f"entrada {i}: separador Windows em {path!r}"
    causa = entry["causa"]
    assert isinstance(causa, str) and causa, f"entrada {i}: causa vazia"
    assert "/" not in causa and "\\" not in causa, f"entrada {i}: causa {causa!r}"
    sha = entry["sha256"]
    assert isinstance(sha, str) and _SHA.fullmatch(sha) is not None, f"entrada {i}: sha {sha!r}"
    for dim in ("width", "height"):
        val = entry[dim]
        assert type(val) is int and val > 0, f"entrada {i}: {dim}={val!r}"
    assert entry["orientation"] in ORIENTATIONS, f"entrada {i}: orientation {entry['orientation']!r}"
    assert entry["tem_pessoas"] is True or entry["tem_pessoas"] is False or entry["tem_pessoas"] is None, \
        f"entrada {i}: tem_pessoas={entry['tem_pessoas']!r}"
    for key in BINARY_KEYS:
        assert key not in entry, f"entrada {i}: chave binária {key!r}"


def test_index_existe_e_e_json_valido():
    doc = _load_index()
    assert isinstance(doc, (list, dict)), "topo deve ser lista ou objeto"
    # LACUNA: sem nome de schema/versão declarado para este índice.


def test_indice_tem_145_entradas_raster():
    assert len(_entries(_load_index())) == 145


def test_contagem_por_extensao_raster():
    counts = {suf: 0 for suf in RASTER_COUNT}
    for i, entry in enumerate(_entries(_load_index())):
        path = entry.get("path") if isinstance(entry, dict) else None
        assert isinstance(path, str) and path, f"entrada {i}: path ausente"
        suf = PurePosixPath(path).suffix
        assert suf in counts, f"entrada {i}: extensão fora do contrato: {path!r}"
        counts[suf] += 1
    assert counts == RASTER_COUNT, f"contagem por extensão: {counts}"

def test_paths_relativos_unicos_sem_fuga():
    seen = set()
    for i, entry in enumerate(_entries(_load_index())):
        assert isinstance(entry, dict), f"entrada {i}: objeto esperado"
        path = entry.get("path")
        assert isinstance(path, str) and path, f"entrada {i}: path ausente"
        assert not PurePosixPath(path).is_absolute(), f"entrada {i}: absoluto {path!r}"
        assert ".." not in PurePosixPath(path).parts, f"entrada {i}: '..' em {path!r}"
        assert "\\" not in path, f"entrada {i}: separador Windows em {path!r}"
        assert path not in seen, f"entrada {i}: duplicado {path!r}"
        seen.add(path)
    assert len(seen) == 145

def test_campos_obrigatorios_e_tipos():
    for i, entry in enumerate(_entries(_load_index())):
        _check_entry(entry, i)

def test_orientacao_confere_com_dimensoes():
    for i, entry in enumerate(_entries(_load_index())):
        assert isinstance(entry, dict), f"entrada {i}: objeto esperado"
        w, h = entry.get("width"), entry.get("height")
        assert type(w) is int and type(h) is int and w > 0 and h > 0, f"entrada {i}: dimensões"
        esperado = "quadrada" if w == h else ("paisagem" if w > h else "retrato")
        assert entry.get("orientation") == esperado, f"entrada {i}: {w}x{h} deveria ser {esperado}"

def test_sem_mp4_pdf_nem_carga_binaria():
    # LACUNA: o motivo da exclusão do .mp4/PDF não tem campo nomeado; só a ausência é verificável.
    for i, entry in enumerate(_entries(_load_index())):
        assert isinstance(entry, dict), f"entrada {i}: objeto esperado"
        path = entry.get("path")
        assert isinstance(path, str), f"entrada {i}: path não-str"
        assert not path.lower().endswith((".mp4", ".pdf")), f"entrada {i}: excluído presente: {path!r}"
        for key in BINARY_KEYS:
            assert key not in entry, f"entrada {i}: carga binária em {key!r}"

def test_causas_sao_nomes_de_pasta():
    causas = set()
    for i, entry in enumerate(_entries(_load_index())):
        assert isinstance(entry, dict), f"entrada {i}: objeto esperado"
        causa = entry.get("causa")
        assert isinstance(causa, str) and causa, f"entrada {i}: causa vazia"
        assert "/" not in causa and "\\" not in causa, f"entrada {i}: causa {causa!r}"
        causas.add(causa)
    assert 1 <= len(causas) <= 11, f"acervo tem 11 pastas; causas: {sorted(causas)}"

def test_fotos_nao_duplicadas_no_assets_index():
    assets = Path(__file__).resolve().parents[1] / ASSETS_REL
    if not assets.is_file():
        pytest.skip(f"{ASSETS_REL} ainda não existe (lane L-ASSETS-INDEX-01)")
    doc = json.loads(assets.read_text(encoding="utf-8"))
    conhecidos = {a.get("path") for a in doc.get("assets", []) if isinstance(a, dict)}
    fotos = {e["path"] for e in _entries(_load_index()) if isinstance(e, dict)}
    assert not (fotos & conhecidos), "fotos duplicadas no assets-index"
