"""Contrato: `set_pic` enquadra a foto no quadro do template (recorte `cover` centrado ou pelo ponto focal), sem esticar."""
import pytest
from PIL import Image
from pptx import Presentation
from pptx.util import Inches

from forja import pptx_deck


def _slide_com_quadro(tmp_path, quadro_w, quadro_h, crop_inicial=None):
    base = tmp_path / "base.png"
    Image.new("RGB", (10, 10), "white").save(base)
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    pic = slide.shapes.add_picture(str(base), Inches(1), Inches(1), Inches(quadro_w), Inches(quadro_h))
    pic.name = "foto"
    if crop_inicial:
        pic.crop_left = pic.crop_right = crop_inicial
    return slide, pic


def _imagem(tmp_path, w, h, nome="nova.png"):
    caminho = tmp_path / nome
    Image.new("RGB", (w, h), "red").save(caminho)
    return caminho


def _visivel(pic, w, h):
    return (w * (1 - pic.crop_left - pic.crop_right)) / (h * (1 - pic.crop_top - pic.crop_bottom))


def test_imagem_larga_em_quadro_quadrado_recorta_os_lados_centrado(tmp_path):
    slide, pic = _slide_com_quadro(tmp_path, 2, 2)
    pptx_deck.set_pic(slide, "foto", _imagem(tmp_path, 2000, 1000))
    assert (round(pic.crop_left, 4), round(pic.crop_right, 4)) == (0.25, 0.25)
    assert (pic.crop_top, pic.crop_bottom) == (0, 0)
    assert _visivel(pic, 2000, 1000) == pytest.approx(1.0, abs=0.001)


def test_imagem_alta_em_quadro_largo_recorta_cima_e_baixo(tmp_path):
    slide, pic = _slide_com_quadro(tmp_path, 4, 2)
    pptx_deck.set_pic(slide, "foto", _imagem(tmp_path, 1000, 2000))
    assert (round(pic.crop_top, 4), round(pic.crop_bottom, 4)) == (0.375, 0.375)
    assert (pic.crop_left, pic.crop_right) == (0, 0)
    assert _visivel(pic, 1000, 2000) == pytest.approx(2.0, abs=0.001)


def test_mesma_proporcao_nao_recorta(tmp_path):
    slide, pic = _slide_com_quadro(tmp_path, 4, 2)
    pptx_deck.set_pic(slide, "foto", _imagem(tmp_path, 2000, 1000))
    assert (pic.crop_left, pic.crop_right, pic.crop_top, pic.crop_bottom) == (0, 0, 0, 0)


def test_recorte_do_template_e_substituido(tmp_path):
    slide, pic = _slide_com_quadro(tmp_path, 2, 2, crop_inicial=0.3)
    pptx_deck.set_pic(slide, "foto", _imagem(tmp_path, 1000, 1000))
    assert (pic.crop_left, pic.crop_right) == (0, 0)


def test_ponto_focal_desloca_o_recorte(tmp_path):
    slide, pic = _slide_com_quadro(tmp_path, 2, 2)
    pptx_deck.set_pic(slide, "foto", _imagem(tmp_path, 2000, 1000), focal=(0.0, 0.5))
    assert (round(pic.crop_left, 4), round(pic.crop_right, 4)) == (0.0, 0.5)
    slide2, pic2 = _slide_com_quadro(tmp_path, 2, 2)
    pptx_deck.set_pic(slide2, "foto", _imagem(tmp_path, 2000, 1000), focal=(1.0, 0.5))
    assert (round(pic2.crop_left, 4), round(pic2.crop_right, 4)) == (0.5, 0.0)
