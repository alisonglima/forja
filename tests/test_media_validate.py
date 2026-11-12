"""Contrato `forja.media_validate` (L-T-MV-01, plano:842; congela 771/742/810/338):
validate_media(path,spec)->list[dict]; bytes/pixels/razao tol 0,01; magic+Pillow still,
ffprobe injetavel video; MEDIA_BYTES/PIXELS/RATIO/FORMAT de modulo; limites formats.json.
Issues qa.py:13-14 ({level,code,msg}); sem ERROR_CODES novos."""
from __future__ import annotations

import struct
import zlib

import pytest


def _png(path, width, height):
    def chunk(t, d):
        h = struct.pack(">I", len(d)) + t + d
        return h + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    return path

def _spec(**over):
    # LACUNA: chaves obrigatorias de spec alem destas (plano:338) nao decididas.
    base = {"largura": 2, "altura": 2, "razao": "1:1", "limite_bytes": 1 << 20, "duracao_max_s": None}
    base.update(over)
    return base

def _mp4(path):
    path.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom")
    return path

def _probe(monkeypatch, width, height):
    # LACUNA: "ffprobe injetavel" (742) sem seam; injeta via forja.probe.probe_video (810).
    # LACUNA: duracao_max_s (338) sem codigo em 742; duracao nao afirmada aqui.
    from forja import probe
    payload = {"duration": 5.0, "width": width, "height": height, "fps": 30.0, "has_audio": True}
    monkeypatch.setattr(probe, "probe_video", lambda p, *a, **k: dict(payload))

def test_matching_still_passes(tmp_path):
    from forja import media_validate
    path = _png(tmp_path / "ok.png", 2, 2)
    assert media_validate.validate_media(path, _spec()) == []

def test_bytes_over_limit_reports_media_bytes(tmp_path):
    from forja import media_validate
    path = _png(tmp_path / "big.png", 2, 2)
    tiny = path.stat().st_size - 1
    (issue,) = media_validate.validate_media(path, _spec(limite_bytes=tiny))
    assert (issue["level"], issue["code"]) == ("error", "MEDIA_BYTES") and {"level", "code", "msg"} <= set(issue)

def test_scaled_still_reports_media_pixels(tmp_path):
    from forja import media_validate
    path = _png(tmp_path / "ama.png", 2, 2)
    (issue,) = media_validate.validate_media(path, _spec(largura=1, altura=1, razao="1:1"))
    assert (issue["level"], issue["code"]) == ("error", "MEDIA_PIXELS")

def test_ratio_beyond_tolerance_reports_media_ratio(tmp_path):
    from forja import media_validate
    path = _png(tmp_path / "wide.png", 200, 100)
    issues = media_validate.validate_media(path, _spec(largura=100, altura=100, razao="1:1"))
    found = [i for i in issues if i["code"] == "MEDIA_RATIO"]
    assert len(found) == 1 and found[0]["level"] == "error" and all(i["level"] == "error" for i in issues)

def test_ratio_inside_tolerance_passes(tmp_path):
    from forja import media_validate
    # |100/100-100/101| ~= 0,0099 < 0,01: passa sem MEDIA_RATIO.
    # LACUNA: a borda exata (=0,01, inclusiva ou exclusiva) nao e decidida.
    path = _png(tmp_path / "q.png", 100, 100)
    assert media_validate.validate_media(path, _spec(largura=100, altura=100, razao="100:101")) == []

def test_wrong_magic_reports_media_format(tmp_path):
    from forja import media_validate
    path = tmp_path / "falso.png"
    path.write_bytes(b"isto nao e uma imagem nem um video")
    issues = media_validate.validate_media(path, _spec())
    assert any(i["code"] == "MEDIA_FORMAT" and i["level"] == "error" for i in issues)
    assert all(i["level"] == "error" for i in issues)

def test_truncated_png_reports_media_format(tmp_path):
    from forja import media_validate
    path = tmp_path / "corte.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR\x00")
    issues = media_validate.validate_media(path, _spec())
    assert any(i["code"] == "MEDIA_FORMAT" and i["level"] == "error" for i in issues)

def test_empty_file_reports_media_format(tmp_path):
    from forja import media_validate
    path = tmp_path / "vazio.png"
    path.write_bytes(b"")
    issues = media_validate.validate_media(path, _spec())
    assert any(i["code"] == "MEDIA_FORMAT" and i["level"] == "error" for i in issues)

def test_missing_file_fails_closed(tmp_path):
    from forja import media_validate
    try: issues = media_validate.validate_media(tmp_path / "ausente.png", _spec())
    except OSError: return
    assert issues != [] and all(i["level"] == "error" for i in issues)

def test_dotdot_to_valid_file_passes(tmp_path):
    from forja import media_validate
    # LACUNA: sem sandbox de traversal no contrato; ".." p/ arquivo valido valida normal.
    (tmp_path / "sub").mkdir()
    path = _png(tmp_path / "ok.png", 2, 2)
    assert media_validate.validate_media(tmp_path / "sub" / ".." / path.name, _spec()) == []

def test_string_spec_raises(tmp_path):
    from forja import media_validate
    path = _png(tmp_path / "ok.png", 2, 2)
    with pytest.raises(Exception):
        media_validate.validate_media(path, "nao-um-dict")

def test_matching_video_passes(tmp_path, monkeypatch):
    from forja import media_validate
    _probe(monkeypatch, 1080, 1920)
    path = _mp4(tmp_path / "ok.mp4")
    assert media_validate.validate_media(path, _spec(largura=1080, altura=1920, razao="9:16", duracao_max_s=60)) == []

def test_video_pixels_mismatch_reports_media_pixels(tmp_path, monkeypatch):
    from forja import media_validate
    _probe(monkeypatch, 720, 1280)
    path = _mp4(tmp_path / "peq.mp4")
    issues = media_validate.validate_media(path, _spec(largura=1080, altura=1920, razao="9:16", duracao_max_s=60))
    assert "MEDIA_PIXELS" in [i["code"] for i in issues] and "MEDIA_RATIO" not in [i["code"] for i in issues]
