"""Contrato da CLI de slides: `forja slides`, `approve --slides` e `doctor`.

:1840 flags `--project/--deck/--template/--sources/--out/--only/--force/--json/
--captures 1280,360`; `--template` sem default -> `DECK_TEMPLATE_MISSING` exit 4
(:1757/:2508). `deck.variant` e slug de `variants.json`, nunca flag (:1692):
ausente -> `BRAND_VARIANT_REQUIRED`, fora -> `CONFIG_INVALID`. Exit codes
(:2508-2514): DECK_SCHEMA 2, DECK_TEMPLATE_MISSING 4, DECK_SHAPE_MISSING 1,
DECK_CONVERT_FAILED 3 (repetivel), ASSET_HASH_MISMATCH 1, VARIANT 2.
`approve --slides --hash` repetivel, `--by` obrigatorio, um hash so nao aprova
(:1820/:1840). Doctor: 4 checks sem segredo/caminho absoluto (:1844); falha
`--json` sem traceback (:401). # LACUNA: schema de `variants.json`/erro de
`--hash` ausente nao fixados; `deck.variant` fica em T-SLIDES-01.
"""
import hashlib
import io
import json

import pytest

SLIDES_CHECKS = ("python:pptx", "soffice", "brand_sources", "pptx_template")

def _run(argv, env=None):
    from forja import cli

    out, err = io.StringIO(), io.StringIO()
    code = cli.main(argv, env={} if env is None else env, out=out, err=err)
    return code, out.getvalue(), err.getvalue()

def _json(argv, env=None):
    code, out, err = _run(argv, env=env)
    return code, json.loads(out), out, err

def _project(tmp_path):
    root = tmp_path / "deck"
    (root / "out").mkdir(parents=True)
    (root / "config.yaml").write_text("project:\n  name: deck\n  workflow: slides\n", encoding="utf-8")
    return root

def _doctor(tmp_path, tools=("ffmpeg", "ffprobe")):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for tool in tools:
        (bin_dir / tool).write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (bin_dir / tool).chmod(0o755)
    return _json(["--json", "doctor"], env={"PATH": str(bin_dir)})

def _approve(root, *extra):
    return _json(["--json", "--project", str(root), "approve", "--slides", *extra])

def test_slides_accepts_every_documented_flag(tmp_path):
    root, sources = _project(tmp_path), tmp_path / "fontes"
    sources.mkdir()
    _, doc, _, _ = _json([
        "--json", "--project", str(root), "slides", "--deck", "deck.yaml",
        "--template", "lions-oficial-2022", "--sources", str(sources),
        "--out", "out", "--only", "deck", "--force", "--captures", "1280,360",
    ])
    # `variant` nao e flag (:1692): vem do deck.yaml. Nenhuma flag documentada
    # pode ser recusada como USAGE.
    assert doc.get("error", {}).get("code") != "USAGE"

def test_slides_without_template_fails_with_the_exact_envelope(tmp_path):
    code, doc, out, err = _json(["--json", "--project", str(_project(tmp_path)), "slides"])
    assert code == 4 and doc["ok"] is False
    assert set(doc) == {"ok", "error"}
    assert set(doc["error"]) == {"code", "msg", "hint", "retryable", "details"}
    assert doc["error"]["code"] == "DECK_TEMPLATE_MISSING"
    assert doc["error"]["retryable"] is False
    assert "Traceback" not in out + err

@pytest.mark.parametrize("code, exit_code, retryable", [
    ("DECK_SCHEMA", 2, False),
    ("DECK_TEMPLATE_MISSING", 4, False),
    ("DECK_SHAPE_MISSING", 1, False),
    ("DECK_CONVERT_FAILED", 3, True),
    ("ASSET_HASH_MISMATCH", 1, False),
    ("BRAND_VARIANT_REQUIRED", 2, False),
    ("CONFIG_INVALID", 2, False),
])
def test_slides_error_codes_follow_the_contract(code, exit_code, retryable):
    from forja.errors import ERROR_CODES

    assert set(ERROR_CODES[code]) == {"exit", "retryable", "hint"}
    assert (ERROR_CODES[code]["exit"], ERROR_CODES[code]["retryable"]) == (exit_code, retryable)

def test_doctor_reports_the_four_slides_checks(tmp_path):
    code, doc, out, _ = _doctor(tmp_path)
    checks = {item["name"]: item for item in doc["data"]["checks"]}
    assert code == 0 and set(SLIDES_CHECKS) <= set(checks)
    for name in SLIDES_CHECKS:
        detail = checks[name]["detail"]
        assert isinstance(detail, str) and detail.strip()
        assert not detail.startswith("/") and str(tmp_path) not in detail
    assert "Traceback" not in out

def test_doctor_without_ffmpeg_exits_missing_prereq_with_the_checks(tmp_path):
    code, doc, _, _ = _doctor(tmp_path, tools=())
    assert code == 4 and doc["error"]["code"] == "MISSING_PREREQ"
    assert set(SLIDES_CHECKS) <= {item["name"] for item in doc["error"]["details"]["checks"]}

def test_approve_slides_records_one_artifact_per_hash(tmp_path):
    root = _project(tmp_path)
    pptx, pdf = root / "out" / "deck.pptx", root / "out" / "deck.pdf"
    pptx.write_bytes(b"pptx")
    pdf.write_bytes(b"pdf")
    code, doc, _, _ = _approve(root, "--hash", str(pptx), "--hash", str(pdf), "--by", "Ana")
    assert code == 0 and doc["data"]["approvals"]["by"] == "Ana"
    assert {(item["path"], item["sha256"], item["bytes"]) for item in doc["data"]["approvals"]["artifacts"]} == {
        ("out/deck.pptx", hashlib.sha256(b"pptx").hexdigest(), 4),
        ("out/deck.pdf", hashlib.sha256(b"pdf").hexdigest(), 3),
    }

@pytest.mark.parametrize("extra", [(), ("--by", "")])
def test_approve_slides_requires_a_non_empty_by(tmp_path, extra):
    deck = _project(tmp_path) / "out" / "deck.pptx"
    deck.write_bytes(b"x")
    code, doc, _, _ = _approve(tmp_path / "deck", "--hash", str(deck), *extra)
    assert code == 2 and doc["ok"] is False

def test_approve_slides_with_one_hash_does_not_record_artifacts(tmp_path):
    root = _project(tmp_path)
    deck = root / "out" / "deck.pptx"
    deck.write_bytes(b"x")
    code, doc, _, _ = _approve(root, "--hash", str(deck), "--by", "Ana")
    saved = root / "approvals.json"
    assert code != 0 and doc["ok"] is False
    assert not saved.exists() or not json.loads(saved.read_text(encoding="utf-8")).get("artifacts")

def test_approve_slides_fails_closed_on_corrupt_approvals(tmp_path):
    root = _project(tmp_path)
    (root / "approvals.json").write_text("{quebrado", encoding="utf-8")
    pptx, pdf = root / "out" / "deck.pptx", root / "out" / "deck.pdf"
    pptx.write_bytes(b"pptx")
    pdf.write_bytes(b"pdf")
    code, doc, _, _ = _approve(root, "--hash", str(pptx), "--hash", str(pdf), "--by", "Ana")
    assert code == 1 and doc["error"]["code"] == "GATE_FAILED"
    assert (root / "approvals.json").read_text(encoding="utf-8") == "{quebrado"
