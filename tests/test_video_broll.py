"""Contrato T-VID-BROLL-01A: validacao do b-roll em `forja/broll.py`.
Congela L-VID-BROLL-01 (plano:2607): b-roll 9:16/1080p validado, nunca
ampliado localmente — o upscale 720p→1080p e feito no Flow (Conta 1) e
ingerido (plano:2571); asset ausente vira ASSET_MISSING (plano:2639).
Timeline, ordem, duracao, corte e legenda sao de T-VID-BROLL-01B (plano:2640).
Retorno: lista de issues {level,id,code,msg}; `probe=` injetavel; sem rede,
`sleep` ou relogio real. LACUNAs marcadas com `# LACUNA:` no corpo.
"""
import pytest

# LACUNA: contrato nao nomeia funcao/assinatura; congela-se validate_broll(path, root=..., probe=...).


def _probe(width=1080, height=1920):
    calls = []

    def fake(path):
        calls.append(str(path))
        return {"duration": 8.0, "width": width, "height": height, "fps": 30.0, "has_audio": False}

    fake.calls = calls
    return fake


def _touch(root, name):
    (root / name).write_bytes(b"\x00")  # placeholder; medidas vem do probe
    return name


def _for(code, issues):
    return [i for i in issues if i.get("code") == code]


def test_valid_1080x1920_broll_uses_injected_probe(tmp_path):
    from forja import broll

    fake = _probe()
    name = _touch(tmp_path, "broll.mp4")
    assert broll.validate_broll(name, root=tmp_path, probe=fake) == []
    assert len(fake.calls) == 1 and fake.calls[0].endswith("broll.mp4")


def test_rejects_flow_720x1280_instead_of_upscaling(tmp_path):
    from forja import broll

    name = _touch(tmp_path, "broll720.mp4")
    issues = broll.validate_broll(name, root=tmp_path, probe=_probe(720, 1280))
    errs = _for("MEDIA_PIXELS", issues)
    assert len(errs) == 1 and errs[0]["level"] == "error"


def test_rejects_1280x720_landscape(tmp_path):
    from forja import broll

    name = _touch(tmp_path, "paisagem.mp4")
    issues = broll.validate_broll(name, root=tmp_path, probe=_probe(1280, 720))
    errs = _for("MEDIA_RATIO", issues)
    assert len(errs) == 1 and errs[0]["level"] == "error"


def test_rejects_off_by_one_pixel_width(tmp_path):
    from forja import broll

    # LACUNA: tolerancia 0,01 (plano:742) vale p/ razao, nao p/ pixels.
    name = _touch(tmp_path, "quase.mp4")
    issues = broll.validate_broll(name, root=tmp_path, probe=_probe(1079, 1920))
    errs = _for("MEDIA_PIXELS", issues)
    assert len(errs) == 1 and errs[0]["level"] == "error"


def test_missing_asset_reports_asset_missing(tmp_path):
    from forja import broll

    # LACUNA: contrato nao diz se ha busca por id em manifesto; aqui caminho direto.
    issues = broll.validate_broll("nao-existe.mp4", root=tmp_path, probe=_probe())
    assert len(issues) == 1
    (only,) = issues
    assert set(only) == {"level", "id", "code", "msg"}
    assert (only["level"], only["code"]) == ("error", "ASSET_MISSING")


@pytest.mark.parametrize("given", ["", None])
def test_empty_or_none_path_reports_asset_missing(tmp_path, given):
    from forja import broll

    fake = _probe()
    issues = broll.validate_broll(given, root=tmp_path, probe=fake)
    assert [i["code"] for i in issues] == ["ASSET_MISSING"]
    assert [i["level"] for i in issues] == ["error"]
    assert fake.calls == []


@pytest.mark.parametrize("given", ["../fora.mp4", "/tmp/fora.mp4"])
def test_path_escape_is_rejected_without_touching_disk(tmp_path, given):
    from forja import broll

    # Precedente: storyboard.py marca fuga da raiz como ASSET_OUTSIDE (issue error).
    fake = _probe()
    issues = broll.validate_broll(given, root=tmp_path, probe=fake)
    assert [i["code"] for i in issues] == ["ASSET_OUTSIDE"]
    assert [i["level"] for i in issues] == ["error"]
    assert fake.calls == []


def test_unreadable_media_fails_closed(tmp_path):
    from forja import broll

    def bad_probe(path):
        raise RuntimeError("ffprobe falhou")

    name = _touch(tmp_path, "corte.mp4")
    issues = broll.validate_broll(name, root=tmp_path, probe=bad_probe)
    assert [i["code"] for i in issues] == ["MEDIA_BYTES"]
    assert [i["level"] for i in issues] == ["error"]


def test_wrong_typed_probe_payload_fails_closed(tmp_path):
    from forja import broll

    def odd_probe(path):
        return {"duration": 8.0, "width": "largo", "height": 1920, "fps": 30.0, "has_audio": False}

    name = _touch(tmp_path, "estranho.mp4")
    issues = broll.validate_broll(name, root=tmp_path, probe=odd_probe)
    assert [i["code"] for i in issues] == ["MEDIA_PIXELS"]
    assert [i["level"] for i in issues] == ["error"]


def test_source_has_no_local_upscaler():
    from pathlib import Path

    import forja.broll as mod

    # Sem ampliacao local (plano:2571): 720p→1080p so no Flow; auditoria estatica.
    src = Path(mod.__file__).read_text(encoding="utf-8").lower()
    banned = ("scale=", "zscale", ".resize(", "thumbnail(", "lanczos", "cv2", "sws_flags")
    assert [tok for tok in banned if tok in src] == []
