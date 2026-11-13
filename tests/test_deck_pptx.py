"""Contrato L-OD-T12 de forja/pptx_deck.py (T-DECK-PPTX-01): pptx sintetico."""
from __future__ import annotations
import hashlib
import pytest
from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
def _png(path, rgb):
    from PIL import Image
    Image.new("RGB", (12, 12), rgb).save(str(path))
def _base(tmp):
    prs = Presentation()
    prs.slide_layouts[6].name = "L26"
    s = prs.slides.add_slide(prs.slide_layouts[6])
    b = s.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
    b.name = "titulo"
    tf = b.text_frame
    tf.clear()
    r = tf.paragraphs[0].add_run()
    r.text = "ola"
    r.font.size = Pt(24)
    r.font.bold = True
    tf.add_paragraph().add_run().text = "sobra"
    _png(tmp / "a.png", (255, 0, 0))
    p = s.shapes.add_picture(str(tmp / "a.png"), Inches(0.5), Inches(0.5), Inches(1), Inches(1))
    p.name = "foto"
    p.crop_left = 0.1
    s.notes_slide.notes_text_frame.text = "nota1"
    return prs, s, b, p
def _dup(tmp):
    prs, s, b, p = _base(tmp)
    c = s.shapes.add_textbox(Inches(1), Inches(3), Inches(3), Inches(1))
    c.name = "titulo"
    c.text_frame.text = "beta trecho"
    return prs, s
def test_clone_copia_texto_imagem_notas(tmp_path):
    from forja import pptx_deck
    prs, s, b, p = _base(tmp_path)
    out = pptx_deck.clone(prs, s)
    assert len(prs.slides) == 2 and out is prs.slides[-1]
    assert sorted(x.name for x in out.shapes) == sorted(x.name for x in s.shapes)
    assert "ola" in [x for x in out.shapes if x.name == "titulo"][0].text_frame.text
    assert out.notes_slide.notes_text_frame.text == "nota1"
def test_clone_remapeia_relacao(tmp_path):
    from forja import pptx_deck
    prs, s, b, p = _base(tmp_path)
    out = pptx_deck.clone(prs, s)
    pic = [x for x in out.shapes if x.name == "foto"][0]
    rid = pic._element.blipFill.blip.get(qn("r:embed"))
    assert out.part.related_part(rid).blob == p.image.blob
def test_put_preserva_rpr_e_colapsa(tmp_path):
    from forja import pptx_deck
    prs, s, b, p = _base(tmp_path)
    pptx_deck.put(s, "titulo", "novo")
    tf = [x for x in s.shapes if x.name == "titulo"][0].text_frame
    assert len(tf.paragraphs) == 1 and tf.text == "novo"
    assert tf.paragraphs[0].runs[0]._r.get_or_add_rPr().get("sz") == "2400"
    assert tf.paragraphs[0].runs[0].font.bold
def test_put_nome_ausente(tmp_path):
    from forja import pptx_deck
    from forja.errors import ForjaError
    prs, s, b, p = _base(tmp_path)
    with pytest.raises(ForjaError) as exc:
        pptx_deck.put(s, "nada", "x")
    assert exc.value.code == "DECK_SHAPE_MISSING"
def test_put_duplicado_sem_contains(tmp_path):
    from forja import pptx_deck
    from forja.errors import ForjaError
    prs, s = _dup(tmp_path)
    with pytest.raises(ForjaError) as exc:
        pptx_deck.put(s, "titulo", "novo")
    assert exc.value.code == "DECK_SHAPE_MISSING"
def test_put_duplicado_com_contains(tmp_path):
    from forja import pptx_deck
    prs, s = _dup(tmp_path)
    pptx_deck.put(s, "titulo", "novo", contains="trecho")
    assert sorted(x.text_frame.text for x in s.shapes if x.name == "titulo") == ["novo", "ola\nsobra"]
def test_set_pic_troca_blob_mantem_geometria(tmp_path):
    from forja import pptx_deck
    prs, s, b, p = _base(tmp_path)
    geom = (p.left, p.top, p.width, p.height)  # o recorte e recalculado pelo enquadramento `cover` (tests/test_set_pic_cover.py)
    old = p.image.blob
    _png(tmp_path / "b.png", (0, 255, 0))
    pptx_deck.set_pic(s, "foto", str(tmp_path / "b.png"))
    pic = [x for x in s.shapes if x.name == "foto"][0]
    assert (pic.left, pic.top, pic.width, pic.height) == geom
    assert pic.image.blob != old
def test_set_pic_nome_ausente(tmp_path):
    from forja import pptx_deck
    from forja.errors import ForjaError
    prs, s, b, p = _base(tmp_path)
    _png(tmp_path / "b.png", (0, 255, 0))
    with pytest.raises(ForjaError) as exc:
        pptx_deck.set_pic(s, "nada", str(tmp_path / "b.png"))
    assert exc.value.code == "DECK_SHAPE_MISSING"
def test_slim_remove_nao_usado(tmp_path):
    from forja import pptx_deck
    prs, s, b, p = _base(tmp_path)
    assert len(prs.slide_layouts) > 1
    pptx_deck.slim(prs, ())
    assert [x.name for x in prs.slide_layouts] == ["L26"]
def test_slim_mantem_keep_layouts(tmp_path):
    from forja import pptx_deck
    prs, s, b, p = _base(tmp_path)
    prs.slide_layouts[0].name = "L27"
    pptx_deck.slim(prs, ("L27",))
    assert {x.name for x in prs.slide_layouts} == {"L26", "L27"}
def test_validate_feliz(tmp_path):
    from forja import pptx_deck
    prs, s, b, p = _base(tmp_path)
    out = tmp_path / "d.pptx"
    prs.save(str(out))
    assert pptx_deck.validate(str(out), {"slides": 1, "layouts": ["L26"]}, hashlib.sha256(out.read_bytes()).hexdigest()) == []
def test_validate_slides_errado(tmp_path):
    from forja import pptx_deck
    prs, s, b, p = _base(tmp_path)
    out = tmp_path / "d.pptx"
    prs.save(str(out))
    issues = pptx_deck.validate(str(out), {"slides": 2, "layouts": ["L26"]}, hashlib.sha256(out.read_bytes()).hexdigest())
    assert any(i["level"] == "error" and i["code"] == "DECK_SCHEMA" for i in issues)
def test_validate_sha_errado(tmp_path):
    from forja import pptx_deck
    prs, s, b, p = _base(tmp_path)
    out = tmp_path / "d.pptx"
    prs.save(str(out))
    issues = pptx_deck.validate(str(out), {"slides": 1, "layouts": ["L26"]}, "0" * 64)
    assert any(i["level"] == "error" and i["code"] == "DECK_SCHEMA" for i in issues)
