"""Contrato do gerador da doc web (scripts/build-doc.py): HTML unico, offline, com os prompts embutidos literalmente."""
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build-doc.py"
SECTIONS = ["visao-geral", "modo-simples", "modo-avancado", "arquitetura", "prompts", "seguranca", "licencas", "navegador", "problemas"]


def _build(tmp_path, name="guia.html"):
    out = tmp_path / name
    proc = subprocess.run([sys.executable, "-I", str(SCRIPT), "--out", str(out)], capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stderr
    return out.read_text(encoding="utf-8")


def _prompts():
    return sorted((ROOT / "prompts").glob("*.md"))


def test_builds_a_single_html_document(tmp_path):
    page = _build(tmp_path)
    assert page.lstrip().lower().startswith("<!doctype html>") and '<html lang="pt-BR"' in page
    assert "<title>" in page and 'name="viewport"' in page


def test_has_every_required_section(tmp_path):
    page = _build(tmp_path)
    for section in SECTIONS:
        assert f'id="{section}"' in page, section


def test_embeds_every_prompt_verbatim_with_a_copy_button(tmp_path):
    page = _build(tmp_path)
    files = _prompts()
    assert len(files) >= 14
    for path in files:
        slug = path.stem
        assert f'data-prompt="{slug}"' in page, slug
        assert f'data-copy="{slug}"' in page, slug
        assert html.escape(path.read_text(encoding="utf-8").strip(), quote=False) in page, slug


def test_is_fully_offline(tmp_path):
    page = _build(tmp_path)
    assert not re.search(r"""(?:src|href)\s*=\s*["']https?://""", page)
    assert "@import" not in page and "fonts.googleapis" not in page
    assert not re.search(r"<script[^>]+src=", page, re.I)


def test_supports_light_and_dark_with_tokens(tmp_path):
    page = _build(tmp_path)
    assert ":root" in page and "prefers-color-scheme: dark" in page
    assert re.search(r"body\s*\{[^}]*background", page)


def test_is_responsive_without_horizontal_scroll(tmp_path):
    page = _build(tmp_path)
    assert "@media" in page and "overflow-wrap" in page


def test_answers_the_chromium_minimized_question(tmp_path):
    page = _build(tmp_path).lower()
    assert "minimizad" in page and "outra área de trabalho" in page


def test_mentions_licenses_and_synthetic_voice_notice(tmp_path):
    page = _build(tmp_path)
    assert "Remotion" in page and "ffmpeg" in page.lower() and "sintetizada" in page.lower()


def test_contains_no_local_paths_or_api_keys(tmp_path):
    page = _build(tmp_path)
    # Montados em partes para o proprio teste nao carregar o literal que ele proibe.
    for word in ("/" + "Users/", "@" + "gmail", "AI" + "za", "sk-"):
        assert word not in page, word

def test_build_is_deterministic(tmp_path):
    assert _build(tmp_path, "a.html") == _build(tmp_path, "b.html")


def test_fails_clearly_when_a_prompt_dir_is_missing(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--out", str(tmp_path / "x.html"), "--prompts", str(tmp_path / "nao-existe")],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert proc.returncode != 0 and "prompts" in (proc.stderr + proc.stdout).lower()


def test_page_has_a_short_size(tmp_path):
    assert len(_build(tmp_path).encode("utf-8")) < 600_000
