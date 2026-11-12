"""Contrato de forja.qa_capture (T-QA-CAPTURE-01).

plano:575 capture_360 grava work/inspect/<peca>-360.png, 360 px de largura.
plano:563 qa_capture gera as capturas 360/1280 (separado de qa_geometry).
plano:576 review exige work/review/<peca>.360.aberta e <peca>.1280.aberta.
plano:630 o registro guarda quem abriu, quando, hash e o que viu.
# LACUNA: assinaturas, nome do arquivo 1280, codigo de erro e formato do
# marcador nao estao no plano; em retrato, §4.7 manda "1280 de largura" e
# K.4 (plano:2408) manda "maior lado em 1280"; aqui a fonte e 1200x630.
"""
import struct
import zlib

import pytest

def _png(path, width, height):
    raw = b"".join(b"\x00" + bytes((12, 34, 56)) * width for _ in range(height))

    def chunk(kind, data):
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    return path


def _dims(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])

def test_capture_360_grava_png_de_360_em_work_inspect(tmp_path):
    from forja import qa_capture
    src = _png(tmp_path / "peca.png", 1080, 1350)
    out = qa_capture.capture_360(src, tmp_path, "post-dia-x")
    assert out == tmp_path / "work" / "inspect" / "post-dia-x-360.png"
    assert _dims(out) == (360, 450)


def test_capture_1280_grava_png_de_1280_em_work_inspect(tmp_path):
    from forja import qa_capture
    src = _png(tmp_path / "peca.png", 1200, 630)
    out = qa_capture.capture_1280(src, tmp_path, "post-dia-x")
    assert out.parent == tmp_path / "work" / "inspect"
    assert _dims(out) == (1280, 672)


def test_capture_recusa_origem_ausente_sem_criar_captura(tmp_path):
    from forja import qa_capture
    from forja.errors import ForjaError
    with pytest.raises(ForjaError):
        qa_capture.capture_360(tmp_path / "nao-existe.png", tmp_path, "peca")
    assert not (tmp_path / "work" / "inspect" / "peca-360.png").exists()


def test_capture_recusa_png_truncado_sem_criar_captura(tmp_path):
    from forja import qa_capture
    from forja.errors import ForjaError
    src = tmp_path / "quebrado.png"
    src.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    with pytest.raises(ForjaError):
        qa_capture.capture_1280(src, tmp_path, "peca")
    saida = tmp_path / "work" / "inspect"
    assert not saida.exists() or not list(saida.iterdir())


def test_record_open_grava_marcadores_360_e_1280(tmp_path):
    from forja import qa_capture
    meta = dict(by="Ana", at="2026-11-11T18:00:00Z", sha256="a" * 64,
                seen="texto e logo ok")
    m360 = qa_capture.record_open(tmp_path, "post-dia-x", 360, **meta)
    m1280 = qa_capture.record_open(tmp_path, "post-dia-x", 1280, **meta)
    review = tmp_path / "work" / "review"
    assert m360 == review / "post-dia-x.360.aberta"
    assert m1280 == review / "post-dia-x.1280.aberta"
    assert sorted(p.name for p in review.iterdir()) == [
        "post-dia-x.1280.aberta", "post-dia-x.360.aberta"]


def test_record_open_registra_quem_quando_hash_e_o_que_viu(tmp_path):
    from forja import qa_capture
    qa_capture.record_open(tmp_path, "post-dia-x", 360, by="Ana",
        at="2026-11-11T18:00:00Z", sha256="b" * 64, seen="CTA legivel a 360 px")
    texto = (tmp_path / "work" / "review" / "post-dia-x.360.aberta").read_text(
        encoding="utf-8")
    for valor in ("Ana", "2026-11-11T18:00:00Z", "b" * 64, "CTA legivel a 360 px"):
        assert valor in texto


def test_record_open_recusa_peca_que_escapa_de_work_review(tmp_path):
    from forja import qa_capture
    from forja.errors import ForjaError
    root = tmp_path / "projeto"
    root.mkdir()
    with pytest.raises(ForjaError):
        qa_capture.record_open(root, "../../../fora", 360, by="Ana",
            at="2026-11-11T18:00:00Z", sha256="c" * 64, seen="x")
    assert not (tmp_path / "fora.360.aberta").exists()
