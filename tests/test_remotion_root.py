"""Contrato do registro da composicao vertical em Root.jsx (T-VID-ROOT-01).

Congela o que o plano decide para L-VID-ROOT-01:
- plano:2610: Root.jsx (EXISTENTE) so ganha o registro da composicao vertical;
- plano:2571: a composicao vertical e 1080x1920 (VerticalBrand, Opening/LowerThird);
- plano:2643: o aceite e a coleta deste arquivo, antes da implementacao existir;
- plano:2649: a PoC exige render 1080x1920 sem quebrar Legendas/Storyboard.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "remotion-template" / "src" / "Root.jsx"


def _source():
    text = ROOT.read_text(encoding="utf-8")
    assert text.strip(), "Root.jsx nao pode estar vazio"
    return text


def _compositions(source):
    return re.findall(r"<Composition\b.*?/>", source, re.S)


def _vertical_names(source):
    match = re.search(
        r'import\s+(?:\{([^}]*)\}|(\w+))\s+from\s+["\']\./VerticalBrand(?:\.jsx)?["\']',
        source,
    )
    assert match, "Root.jsx deve importar de ./VerticalBrand.jsx"
    names = [match.group(2)] if match.group(1) is None else match.group(1).split(",")
    return [part.split(" as ")[-1].strip() for part in names if part.strip()]


def _vertical_compositions(source):
    names = _vertical_names(source)
    blocks = [b for b in _compositions(source)
              if any(re.search(rf"component=\{{\s*{re.escape(n)}(?:\.\w+)?\s*\}}", b) for n in names)]
    assert blocks, "Root.jsx deve registrar a composicao vertical"
    return blocks


def test_root_keeps_legendas_and_storyboard_registered():
    source = _source()
    for name in ("Legendas", "Storyboard"):
        assert re.search(
            rf'import\s*\{{[^}}]*\b{name}\b[^}}]*\}}\s*from\s*["\']\./{name}\.jsx["\']',
            source,
        ), f"import de {name} removido"
        assert any(
            re.search(rf'id\s*=\s*["\']{name}["\']', block)
            and re.search(rf"component=\{{\s*{name}\s*\}}", block)
            for block in _compositions(source)
        ), f"composicao {name} removida"


def test_root_registers_vertical_composition_with_unique_id():
    source = _source()
    vertical = _vertical_compositions(source)
    all_ids = []
    for block in _compositions(source):
        found = re.search(r'id\s*=\s*["\']([^"\']+)["\']', block)
        assert found, "toda Composition precisa de id"
        all_ids.append(found.group(1))
    assert len(all_ids) == len(set(all_ids)), f"ids duplicados: {all_ids}"
    vertical_ids = {re.search(r'id\s*=\s*["\']([^"\']+)["\']', b).group(1) for b in vertical}
    assert not vertical_ids & {"Legendas", "Storyboard"}


def test_vertical_composition_is_1080x1920():
    for block in _vertical_compositions(_source()):
        assert re.search(r"\bwidth=\{1080\}", block), block
        assert re.search(r"\bheight=\{1920\}", block), block


# LACUNA: o plano nao fixa o id, os defaultProps (variant/duracao/fps) nem se
# Opening e LowerThird sao registros separados; por isso so o componente e 1080x1920.
