"""Contrato: `remover` no catalogo tira do slide clonado as formas do modelo que nao tem campo (ex.: icone de imagem, coluna sobrando)."""
import json

import pytest

from tests.test_slides_real import _base, _out, _run


def _com_remover(root, modelo, nomes):
    path = root / "brands" / "leo-lions" / "decks" / "modelos.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["models"][modelo]["remover"] = nomes
    path.write_text(json.dumps(data), encoding="utf-8")


def test_remover_tira_a_forma_nomeada_e_mantem_as_demais(tmp_path):
    import yaml
    _base(tmp_path)
    _com_remover(tmp_path, "capa_foto", ["Subhead"])
    # o deck so preenche o titulo: a forma sem campo (Subhead) e a que o catalogo manda remover
    cat_path = tmp_path / "brands" / "leo-lions" / "decks" / "modelos.json"
    cat = json.loads(cat_path.read_text(encoding="utf-8"))
    cat["models"]["capa_foto"]["campos"].pop("subtitulo")
    cat_path.write_text(json.dumps(cat), encoding="utf-8")
    deck_path = tmp_path / "deck.yaml"
    deck = yaml.safe_load(deck_path.read_text(encoding="utf-8"))
    deck["slides"][0].pop("subtitulo", None)
    deck_path.write_text(yaml.safe_dump(deck, allow_unicode=True), encoding="utf-8")
    _run(tmp_path, "deck", "template", "compose", "pptx")
    _, prs = _out(tmp_path)
    nomes = [s.name for s in prs.slides[0].shapes]
    assert "Subhead" not in nomes and "Headline" in nomes


def test_remover_forma_inexistente_e_erro(tmp_path):
    from forja.errors import ForjaError
    _base(tmp_path)
    _com_remover(tmp_path, "secao", ["NaoExiste"])
    with pytest.raises(ForjaError) as exc:
        _run(tmp_path, "deck", "template", "compose", "pptx")
    assert exc.value.code == "DECK_SHAPE_MISSING"
    assert exc.value.details["campo"] == "NaoExiste"


def test_sem_remover_nada_muda(tmp_path):
    _base(tmp_path)
    _run(tmp_path, "deck", "template", "compose", "pptx")
    _, prs = _out(tmp_path)
    assert [s.name for s in prs.slides[0].shapes] == ["Headline", "Subhead"]


def test_texto_de_modelo_que_sobra_reprova_o_deck(tmp_path):
    """Lorem ipsum / 'Insert ...' do template nao pode chegar ao deck final."""
    import hashlib

    import yaml
    from pptx import Presentation
    from pptx.util import Inches

    from forja.errors import ForjaError
    _base(tmp_path)
    tpl = tmp_path / "tpl.pptx"
    prs = Presentation(str(tpl))
    extra = prs.slides[1].shapes.add_textbox(Inches(1), Inches(4), Inches(3), Inches(1))
    extra.name = "Extra"
    extra.text_frame.text = "Lorem ipsum dolor sit amet"
    prs.save(str(tpl))
    sha = hashlib.sha256(tpl.read_bytes()).hexdigest()
    deck_path = tmp_path / "deck.yaml"
    deck = yaml.safe_load(deck_path.read_text(encoding="utf-8"))
    deck["deck"]["template_sha256"] = sha
    deck_path.write_text(yaml.safe_dump(deck, allow_unicode=True), encoding="utf-8")
    cat_path = tmp_path / "brands" / "leo-lions" / "decks" / "modelos.json"
    cat = json.loads(cat_path.read_text(encoding="utf-8"))
    cat["templates"][0]["sha256"] = sha
    cat_path.write_text(json.dumps(cat), encoding="utf-8")
    with pytest.raises(ForjaError) as exc:
        _run(tmp_path, "deck", "template", "compose", "pptx")
    assert exc.value.code == "DECK_PLACEHOLDER_LEFT"
    assert exc.value.details["slide"] == 3 and exc.value.details["campo"] == "Extra"


def test_chaves_do_deck_cobrem_todos_os_campos_do_catalogo():
    """Todo campo mapeado no catalogo oficial tem de ser aceito pelo passo `deck`."""
    from pathlib import Path

    from forja.workflows import slides
    cat = json.loads((Path(__file__).resolve().parents[1] / "brands/leo-lions/decks/modelos.json").read_text(encoding="utf-8"))
    campos = {c for m in cat["models"].values() for c in (m.get("campos") or {})}
    assert campos - slides._SLIDE_KEYS == set()
