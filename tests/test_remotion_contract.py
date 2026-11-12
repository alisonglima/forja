"""Contrato T-VID-VERT-01: congela L-VID-VERT-01 (plano:2608).

NOVO remotion-template/src/VerticalBrand.jsx: composicao 1080x1920 com
`Opening` e `LowerThird` (plano:2571); aceite PoC (c): still/render
1080x1920 a 30 fps/5 s (150 quadros), sem colisao com legenda (plano:2649);
zona do lower-third acima da faixa da legenda fixada por este teste
(plano:2933 item 13); marca via props `brand` e safe area de 48 px, as
mesmas variaveis do Overlay/kit (plano:1574). Root.jsx/Storyboard.jsx sao
protegidos: so ganham registro/uso em outra lane (plano:2608).
"""
from __future__ import annotations

import re
from pathlib import Path

VERTICAL = Path(__file__).resolve().parents[1] / "remotion-template" / "src" / "VerticalBrand.jsx"


def _read_vertical():
    assert VERTICAL.is_file(), "L-VID-VERT-01 deve criar remotion-template/src/VerticalBrand.jsx"
    return VERTICAL.read_text(encoding="utf-8")


def test_vertical_file_exists():
    assert VERTICAL.is_file(), "L-VID-VERT-01 deve criar remotion-template/src/VerticalBrand.jsx"


def test_vertical_exports_opening():
    src = _read_vertical()
    assert re.search(r"export\s+(const|function)\s+Opening\b", src), "composicao inclui `Opening` (plano:2571)"


def test_vertical_exports_lower_third():
    src = _read_vertical()
    assert re.search(r"export\s+(const|function)\s+LowerThird\b", src), "composicao inclui `LowerThird` (plano:2571)"


def test_vertical_exports_vertical_brand():
    src = _read_vertical()
    assert re.search(r"export\s+(const|function)\s+VerticalBrand\b", src), "composicao 1080x1920 (plano:2571)"


def test_vertical_canvas_is_1080x1920():
    src = _read_vertical()
    assert re.search(r"width\s*[:=]\s*\{?1080\}?", src), "largura 1080 (plano:2649)"
    assert re.search(r"height\s*[:=]\s*\{?1920\}?", src), "altura 1920 (plano:2649)"


def test_vertical_defaults_to_30fps_5s_150_frames():
    src = _read_vertical()
    exact_frames = "150" in src
    five_s_at_30fps = re.search(r"\bfps\s*[:=]\s*\{?30\}?", src) and re.search(
        r"durationS\s*[:=]\s*\{?5\}?", src
    )
    assert exact_frames or five_s_at_30fps, "5 s a 30 fps = 150 quadros (plano:2649)"


def test_vertical_reads_brand_from_props():
    src = _read_vertical()
    assert "brand" in src, "marca chega via props, mesmas chaves do runtime (plano:1574)"
    # LACUNA: o contrato nao fixa o schema exato das props alem de `brand`
    # e `lowerThirds` (nomes de campos de Opening/subs ficam p/ a lane DS).


def test_vertical_safe_margin_is_48():
    src = _read_vertical()
    assert "safe_margin" in src, "usa a variavel de safe area (plano:1574)"
    assert "48" in src, "safe area de 48 px, mesma do kit/Overlay (plano:1574)"


def test_vertical_reuses_captions_and_lower_thirds():
    src = _read_vertical()
    assert "Captions" in src, "reusa o Captions para nao colidir com legenda (plano:2649)"
    assert "lowerThirds" in src, "consome as janelas lowerThirds das props"


def test_vertical_lower_third_above_caption_zone():
    # Zona fixada por este teste (plano:2933 item 13): a legenda base fica na
    # borda 94,5% de 1920 (=1814px); com caixa de ~2 linhas (~100px) a faixa
    # comeca ~1714px do topo, ou seja, ~206px do fundo. O lower-third ancora
    # o fundo em >= 200px para nao invadir a faixa da legenda.
    match = re.search(r"bottom\s*:\s*[\"']?(\d+)", _read_vertical())
    assert match is not None and int(match.group(1)) >= 200


def test_vertical_has_no_absolute_paths():
    # Estilo da casa (AGENTS.md): sem caminhos absolutos no codigo novo.
    src = _read_vertical()
    assert "/Users/" not in src
    assert "/home/" not in src
    assert "/tmp/" not in src
    assert "../" not in src


def test_vertical_source_is_not_empty():
    assert _read_vertical().strip() != ""
    # LACUNA: props hostis (tipo errado, JSON truncado) e render real nao
    # sao exercitaveis em Python sem runtime JS; ficam para a fase PoC (c),
    # que exige still e render 1080x1920/30 fps/5 s (plano:2649).
