"""Contrato forja.contrast_photo (teste; sem implementacao).
plano:734 recorte sob texto; luminancia sRGB + razao por pixel; min/p5/media
com pass/fail vs 4,5:1; video 1 frame/timestamp via ffmpeg com run=, sem
Chrome; CPU, deterministico, passo fixo; issue qa.py codigo CONTRAST_PHOTO.
plano:768 photo_contrast(image,box,text_color,min_ratio=4.5,sample_step=2)
->dict; check_photo_contrast(...)->list[dict]; video_frame(path,at_s,
run=subprocess.run)->bytes. Ver plano:807/2582.
"""
import subprocess
from pathlib import Path

import pytest


def _img(fill, h=8, w=12):
    import numpy as np  # ndarray: convencao de forja/media.py; ver LACUNA-4
    return np.full((h, w, 3), fill, dtype=np.uint8)


def _box():
    # LACUNA-1: box (x,y,w,h)|(x0,y0,x1,y1); (0,0,12,8) cobre 12x8 em ambas.
    return (0, 0, 12, 8)


def _nums(res):
    return [float(v) for v in res.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]


def _verdict(res):
    # LACUNA-2: chaves das estatisticas/veredito sem nome; aceita bool/pass-fail.
    for key in ("pass", "passed", "ok", "status"):
        val = res.get(key)
        if isinstance(val, bool):
            return val
        if str(val).lower() in ("pass", "passed", "ok"):
            return True
        if str(val).lower() in ("fail", "failed", "error"):
            return False
    return next((v for v in res.values() if isinstance(v, bool)), None)


def _near(nums, target, tol=0.15):
    return [v for v in nums if abs(v - target) <= tol]


def test_white_on_black_passes_with_full_ratio():
    from forja import contrast_photo
    res = contrast_photo.photo_contrast(_img(0), _box(), "#FFFFFF")
    assert isinstance(res, dict) and len(_near(_nums(res), 21.0)) >= 3
    assert _verdict(res) is True


def test_same_gray_on_gray_fails_with_unit_ratio():
    from forja import contrast_photo
    res = contrast_photo.photo_contrast(_img(119), _box(), "#777777")
    assert isinstance(res, dict) and len(_near(_nums(res), 1.0)) >= 3
    assert _verdict(res) is False


def test_signature_defaults_and_stats_present():
    from forja import contrast_photo
    import inspect
    sig = inspect.signature(contrast_photo.photo_contrast)
    assert sig.parameters["min_ratio"].default == 4.5
    assert sig.parameters["sample_step"].default == 2
    res = contrast_photo.photo_contrast(_img(0), _box(), "#FFFFFF")
    assert len(_nums(res)) >= 3 and _verdict(res) is not None


def test_same_input_gives_same_result():
    from forja import contrast_photo
    first = contrast_photo.photo_contrast(_img(0), _box(), "#FFFFFF")
    assert contrast_photo.photo_contrast(_img(0), _box(), "#FFFFFF") == first


def test_custom_threshold_changes_verdict():
    from forja import contrast_photo
    assert _verdict(contrast_photo.photo_contrast(_img(0), _box(), "#FFFFFF", min_ratio=22.0)) is False
    assert _verdict(contrast_photo.photo_contrast(_img(119), _box(), "#777777", min_ratio=0.9)) is True


def test_empty_box_raises():
    from forja import contrast_photo
    with pytest.raises(Exception):
        contrast_photo.photo_contrast(_img(0), (0, 0, 0, 0), "#FFFFFF")


def test_wrong_image_type_raises():
    from forja import contrast_photo
    with pytest.raises(Exception):
        contrast_photo.photo_contrast("nao-e-imagem", _box(), "#FFFFFF")


def test_check_returns_issue_with_contrast_photo_code_on_fail():
    from forja import contrast_photo
    issues = contrast_photo.check_photo_contrast(_img(119), _box(), "#777777")
    assert isinstance(issues, list) and len(issues) == 1
    # LACUNA-3: level nao fixado (error|warn); formato qa.py exigido.
    assert issues[0]["code"] == "CONTRAST_PHOTO" and issues[0]["level"] in ("error", "warn")
    assert "id" in issues[0] and isinstance(issues[0]["msg"], str) and issues[0]["msg"]


def test_check_returns_empty_on_pass():
    from forja import contrast_photo
    assert contrast_photo.check_photo_contrast(_img(0), _box(), "#FFFFFF") == []


def test_video_frame_uses_ffmpeg_with_injectable_run(tmp_path):
    from forja import contrast_photo
    calls = []
    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        out = str(cmd[-1])
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_bytes(b"FRAMEBYTES")
        return subprocess.CompletedProcess(cmd, 0, b"FRAMEBYTES", b"")
    src = tmp_path / "clip.mp4"
    src.write_bytes(b"FAKEVIDEO")
    frame = contrast_photo.video_frame(str(src), 1.5, run=fake_run)
    assert isinstance(frame, bytes) and len(frame) > 0
    assert len(calls) == 1 and "ffmpeg" in str(calls[0][0])
    assert any("1.5" in str(a) for a in calls[0])


def test_video_frame_failure_raises(tmp_path):
    from forja import contrast_photo
    def bad_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, b"", b"ffmpeg falhou")
    with pytest.raises(Exception):
        contrast_photo.video_frame(str(tmp_path / "clip.mp4"), 2.0, run=bad_run)


def test_video_frame_parent_traversal_does_not_return_bytes(tmp_path):
    from forja import contrast_photo
    def missing_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, b"", b"arquivo inexistente")
    with pytest.raises(Exception):
        contrast_photo.video_frame(str(tmp_path / ".." / "fora.mp4"), 0.5, run=missing_run)
