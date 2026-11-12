"""Contrato T-DECK-DROP-01 de forja.pptx_deck.drop_slides."""
from __future__ import annotations
import re
import zipfile
import pytest
from pptx import Presentation
from pptx.util import Inches


def _png(path, rgb):
    from PIL import Image
    Image.new("RGB", (1, 1), rgb).save(str(path))


def _deck(n):
    prs = Presentation()
    lay = prs.slide_layouts[6]
    for i in range(n):
        s = prs.slides.add_slide(lay)
        b = s.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
        b.name = "titulo"
        b.text_frame.text = f"s{i}"
    return prs


def _textos(prs):
    return [[x for x in s.shapes if x.name == "titulo"][0].text_frame.text for s in prs.slides]


def test_drop_mantem_apenas_keep_em_ordem():
    from forja import pptx_deck
    prs = _deck(4)
    assert pptx_deck.drop_slides(prs, [1, 3]) is None
    assert len(prs.slides) == 2
    assert _textos(prs) == ["s1", "s3"]


def test_drop_salvo_reaberto_descarta_xml(tmp_path):
    from forja import pptx_deck
    prs = _deck(4)
    pptx_deck.drop_slides(prs, [1, 3])
    path = str(tmp_path / "d.pptx")
    prs.save(path)
    prs2 = Presentation(path)
    assert len(prs2.slides) == 2
    assert _textos(prs2) == ["s1", "s3"]
    slides = [n for n in zipfile.ZipFile(path).namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
    assert len(slides) == 2


def test_drop_remove_midia_do_descartado(tmp_path):
    from forja import pptx_deck
    prs = Presentation()
    lay = prs.slide_layouts[6]
    _png(tmp_path / "a.png", (255, 0, 0))
    _png(tmp_path / "b.png", (0, 0, 255))
    prs.slides.add_slide(lay).shapes.add_picture(str(tmp_path / "a.png"), Inches(0.5), Inches(0.5), Inches(1), Inches(1))
    prs.slides.add_slide(lay).shapes.add_picture(str(tmp_path / "b.png"), Inches(0.5), Inches(0.5), Inches(1), Inches(1))
    pptx_deck.drop_slides(prs, [1])
    path = str(tmp_path / "m.pptx")
    prs.save(path)
    media = [n for n in zipfile.ZipFile(path).namelist() if n.startswith("ppt/media/")]
    assert len(media) == 1


def test_drop_preserva_notas_do_mantido(tmp_path):
    from forja import pptx_deck
    prs = _deck(4)
    prs.slides[1].notes_slide.notes_text_frame.text = "nota-1"
    pptx_deck.drop_slides(prs, [1])
    path = str(tmp_path / "n.pptx")
    prs.save(path)
    assert Presentation(path).slides[0].notes_slide.notes_text_frame.text == "nota-1"


def test_drop_keep_invertido_mantem_ordem_original():
    from forja import pptx_deck
    prs = _deck(4)
    pptx_deck.drop_slides(prs, [3, 1])
    assert _textos(prs) == ["s1", "s3"]


def test_drop_keep_invalido_e_repetido():
    from forja import pptx_deck
    with pytest.raises(ValueError):
        pptx_deck.drop_slides(_deck(4), [])
    with pytest.raises(IndexError):
        pptx_deck.drop_slides(_deck(4), [9])
    prs = _deck(4)
    pptx_deck.drop_slides(prs, [1, 1])
    assert len(prs.slides) == 1
    assert _textos(prs) == ["s1"]


def test_drop_idempotente_com_tudo():
    from forja import pptx_deck
    prs = _deck(4)
    pptx_deck.drop_slides(prs, range(len(prs.slides)))
    assert len(prs.slides) == 4
    assert _textos(prs) == ["s0", "s1", "s2", "s3"]
