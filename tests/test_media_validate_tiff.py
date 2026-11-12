"""Contrato TIFF de `forja.media_validate` (T-GATEFIX-TIFF-01): TIFF still via Pillow."""
from __future__ import annotations


def _spec(**over):
    base = {"largura": 6, "altura": 4, "razao": "3:2", "limite_bytes": 1 << 20, "duracao_max_s": None}
    base.update(over)
    return base


def _tif(path, width=6, height=4):
    from PIL import Image
    Image.new("RGB", (width, height), (200, 30, 30)).save(path, format="TIFF")
    return path


def _png(path, width=6, height=4):
    from PIL import Image
    Image.new("RGB", (width, height), (200, 30, 30)).save(path, format="PNG")
    return path


def test_matching_tiff_passes(tmp_path):
    from forja import media_validate
    path = _tif(tmp_path / "a.tif")
    assert media_validate.validate_media(path, _spec()) == []


def test_tiff_pixels_mismatch_reports_media_pixels(tmp_path):
    from forja import media_validate
    path = _tif(tmp_path / "b.tif")
    issues = media_validate.validate_media(path, _spec(largura=3, altura=2, razao="3:2"))
    assert any(i["code"] == "MEDIA_PIXELS" and i["level"] == "error" for i in issues)


def test_truncated_tiff_reports_single_media_format(tmp_path):
    from forja import media_validate
    path = tmp_path / "corte.tif"
    path.write_bytes(b"II*\x00\x08\x00\x00\x00")
    issues = media_validate.validate_media(path, _spec())
    assert len(issues) == 1
    assert (issues[0]["level"], issues[0]["code"]) == ("error", "MEDIA_FORMAT")
    assert {"level", "code", "msg"} <= set(issues[0])


def test_text_still_reports_media_format(tmp_path):
    from forja import media_validate
    path = tmp_path / "ola.bin"
    path.write_bytes(b"hello world")
    assert any(i["code"] == "MEDIA_FORMAT" and i["level"] == "error"
               for i in media_validate.validate_media(path, _spec()))


def test_matching_png_still_passes(tmp_path):
    from forja import media_validate
    path = _png(tmp_path / "ok.png")
    assert media_validate.validate_media(path, _spec()) == []


# LACUNA: big-endian `b"MM\x00*\x00\x00\x00\x08"` truncado da MEDIA_FORMAT por
# truncamento e nao por assinatura desconhecida; como ambos dao o mesmo codigo,
# nenhum assert aqui distingue os casos, entao nao afirmo o big-endian ativo.
