"""Contrato do QA visual (T-QA-01), congelado antes da implementacao.
Fontes: plano:561-583 (§4.6.8), plano:463-484, plano:2591-2592, plano:2573.
- dimensoes exatas -> FORMAT_UNSUPPORTED; zero estouro (plano:567,570);
- zona segura cruza brand.safe_margin, 48 px nos canvases de 1080 (plano:571);
- CONTRAST_PHOTO na regiao sob o texto: 4.5:1, 3:1 so texto grande (plano:469,569);
- dedup sha256 no mesmo scope/marca em 30 dias -> DUPLICATE_ARTIFACT (plano:574,742);
- issues no formato de qa.py {level,id,code,msg} (forja/qa.py:13-14).
# LACUNA: assinatura/envelope nao ditados pelo plano; este teste os congela.
# LACUNA: PDF A4/A5 RGB e o limite exato de 30 dias nao decididos -> nao testados.
"""
import hashlib
import struct
import zlib

NOW = "2026-11-11T12:00:00+00:00"

def _png(path, width, height):
    raw = b"".join(b"\x00" + b"\x00" * width for _ in range(height))
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(
            ">I", zlib.crc32(body) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    return path

def _box(cid, x, y, w, h):
    return {"id": cid, "x": x, "y": y, "w": w, "h": h}

def _codes(issues):
    return [issue["code"] for issue in issues]

def test_geometry_measure_reads_exact_png_dimensions_bytes_and_sha256(tmp_path):
    from forja import qa_geometry
    png = _png(tmp_path / "peca.png", 1080, 1350)
    out = qa_geometry.measure(png)
    assert (out["width"], out["height"], out["bytes"]) == (1080, 1350, png.stat().st_size)
    assert out["sha256"] == hashlib.sha256(png.read_bytes()).hexdigest()

def test_geometry_measure_returns_none_when_file_is_unmeasurable(tmp_path):
    from forja import qa_geometry
    truncated = tmp_path / "truncada.png"
    truncated.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert qa_geometry.measure(truncated) is None
    assert qa_geometry.measure(tmp_path / "ausente.png") is None

def test_geometry_safe_area_boundary_follows_brand_safe_margin():
    from forja import qa_geometry
    box = _box("logo", 48, 48, 10, 10)
    assert qa_geometry.check_safe_area([box], (1080, 1080)) == []
    issues = qa_geometry.check_safe_area([box], (1080, 1080), safe_margin=64)
    assert _codes(issues) == ["GATE_FAILED"]

def test_geometry_safe_area_flags_box_inside_the_margin():
    from forja import qa_geometry
    issues = qa_geometry.check_safe_area([_box("cta", 47, 48, 100, 40)], (1080, 1080))
    assert [(i["level"], i["id"], i["code"]) for i in issues] == [("error", "cta", "GATE_FAILED")]

def test_geometry_overflow_accepts_flush_edge_and_flags_past_border():
    from forja import qa_geometry
    assert qa_geometry.check_overflow([_box("fundo", 0, 0, 1080, 1080)], (1080, 1080)) == []
    issues = qa_geometry.check_overflow([_box("faixa", 100, 100, 1000, 100)], (1080, 1080))
    assert [(i["level"], i["id"], i["code"]) for i in issues] == [("error", "faixa", "GATE_FAILED")]

def test_visual_happy_path_reports_sha256_and_no_issues(tmp_path):
    from forja import qa_visual
    png = _png(tmp_path / "feed.png", 1080, 1350)
    out = qa_visual.inspect_artifact(png, (1080, 1350), brand_id="leo-lions", hashes=[],
        contrast=[{"id": "headline", "ratio": 5.0, "large_text": False}], now=NOW)
    assert out["ok"] is True and out["issues"] == []
    assert (out["width"], out["height"]) == (1080, 1350)
    assert out["sha256"] == hashlib.sha256(png.read_bytes()).hexdigest()

def test_visual_absent_contrast_and_hash_inputs_are_no_issues(tmp_path):
    from forja import qa_visual
    png = _png(tmp_path / "a.png", 1080, 1080)
    out = qa_visual.inspect_artifact(png, (1080, 1080), brand_id="leo-lions", now=NOW)
    assert out["ok"] is True and out["issues"] == []

def test_visual_wrong_dimensions_are_format_unsupported(tmp_path):
    from forja import qa_visual
    png = _png(tmp_path / "a.png", 1080, 1351)
    out = qa_visual.inspect_artifact(png, (1080, 1350), brand_id="leo-lions", now=NOW)
    assert out["ok"] is False
    assert [(i["level"], i["code"]) for i in out["issues"]] == [("error", "FORMAT_UNSUPPORTED")]

def test_visual_contrast_photo_floor_is_4_5(tmp_path):
    from forja import qa_visual
    png = _png(tmp_path / "a.png", 1080, 1080)
    common = dict(brand_id="leo-lions", hashes=[], now=NOW)
    low = qa_visual.inspect_artifact(png, (1080, 1080), **common, contrast=[{"id": "corpo", "ratio": 4.49, "large_text": False}])
    edge = qa_visual.inspect_artifact(png, (1080, 1080), **common, contrast=[{"id": "corpo", "ratio": 4.5, "large_text": False}])
    assert _codes(low["issues"]) == ["CONTRAST_PHOTO"] and low["ok"] is False
    assert edge["issues"] == []

def test_visual_contrast_photo_large_text_floor_is_3_0(tmp_path):
    from forja import qa_visual
    png = _png(tmp_path / "a.png", 1080, 1080)
    common = dict(brand_id="leo-lions", hashes=[], now=NOW)
    low = qa_visual.inspect_artifact(png, (1080, 1080), **common, contrast=[{"id": "titulo", "ratio": 2.99, "large_text": True}])
    edge = qa_visual.inspect_artifact(png, (1080, 1080), **common, contrast=[{"id": "titulo", "ratio": 3.0, "large_text": True}])
    assert _codes(low["issues"]) == ["CONTRAST_PHOTO"]
    assert edge["issues"] == []

def test_visual_duplicate_artifact_same_brand_within_30_days(tmp_path):
    from forja import qa_visual
    png = _png(tmp_path / "a.png", 1080, 1080)
    digest = hashlib.sha256(png.read_bytes()).hexdigest()
    out = qa_visual.inspect_artifact(png, (1080, 1080), brand_id="leo-lions", now=NOW,
        contrast=[], hashes=[{"hash": digest, "path": "out/post/feed.png", "scope": "leo-lions", "piece": "post-1", "at": "2026-10-20T00:00:00+00:00"}])
    assert _codes(out["issues"]) == ["DUPLICATE_ARTIFACT"]
    assert "out/post/feed.png" in out["issues"][0]["msg"]
    assert "2026-10-20" in out["issues"][0]["msg"]

def test_visual_duplicate_artifact_older_than_30_days_is_not_duplicate(tmp_path):
    from forja import qa_visual
    png = _png(tmp_path / "a.png", 1080, 1080)
    digest = hashlib.sha256(png.read_bytes()).hexdigest()
    out = qa_visual.inspect_artifact(png, (1080, 1080), brand_id="leo-lions", now=NOW,
        contrast=[], hashes=[{"hash": digest, "path": "out/post/velha.png", "scope": "leo-lions", "piece": "post-0", "at": "2026-10-11T00:00:00+00:00"}])
    assert out["issues"] == [] and out["ok"] is True

def test_visual_duplicate_artifact_in_other_brand_is_not_duplicate(tmp_path):
    from forja import qa_visual
    png = _png(tmp_path / "a.png", 1080, 1080)
    digest = hashlib.sha256(png.read_bytes()).hexdigest()
    out = qa_visual.inspect_artifact(png, (1080, 1080), brand_id="leo-lions", now=NOW,
        contrast=[], hashes=[{"hash": digest, "path": "out/outra/feed.png", "scope": "outra-marca", "piece": "post-x", "at": "2026-10-20T00:00:00+00:00"}])
    assert out["issues"] == [] and out["ok"] is True

def test_visual_truncated_png_is_gate_failed(tmp_path):
    from forja import qa_visual
    png = tmp_path / "quebrada.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    out = qa_visual.inspect_artifact(png, (1080, 1080), brand_id="leo-lions", now=NOW)
    assert out["ok"] is False
    assert [(i["level"], i["code"]) for i in out["issues"]] == [("error", "GATE_FAILED")]

def test_visual_inspect_lote_reports_each_piece(tmp_path):
    from forja import qa_visual
    good = _png(tmp_path / "a.png", 1080, 1080)
    bad = _png(tmp_path / "b.png", 1080, 1351)
    out = qa_visual.inspect_lote(
        [{"piece": "a", "path": good, "expected": (1080, 1080)},
         {"piece": "b", "path": bad, "expected": (1080, 1350)}],
        brand_id="leo-lions", hashes=[], now=NOW)
    assert out["ok"] is False
    assert [(i["piece"], i["code"]) for i in out["issues"]] == [("b", "FORMAT_UNSUPPORTED")]
