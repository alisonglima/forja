"""Contrato de consistencia da documentacao e politica de audio do Flow (M3, M4, L1, L4).

Fase 1 (lane fx-t5): so escreve o contrato. Nao implementa nada em
``forja/``, ``scripts/``, ``prompts/`` ou ``docs/``. Outra lane implementa
contra este teste.

O que e verificado:
- M4: ``.env.example``/``kit.sh``/``kit.ps1`` nao dizem que o padrao e
  ``files`` e mencionam ``google_ai_studio``.
- M3 + decisao do dono: prompt 14 / README / guia nao trazem as frases
  erradas ("nao mixa", "Sem audio do clipe", ...); o prompt 14 pede
  somente SFX + som ambiente sem fala/narracao/dialogo/musica, diz que o
  audio embutido entra no bed com ``mode: mute`` removendo, e traz a
  excecao do audio original (dublagem). A secao 04 do guia repete.
- L4: prompt 08 sem bullet repetido.
- L1: quickstart "Escolha as vozes" com ``google_ai_studio`` antes de
  ``piper``, e ``piper`` como alternativa offline opcional.
- Guia versionado == saida fresca do ``build-doc.py``; gerador deterministico.
- Nenhuma prosa afirma que ``status``/``describe`` devolvem ``next_actions``
  sem envelope.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

WRONG_PHRASES = (
    "não mixa",
    "sem áudio do clipe",
    "não use o áudio embutido",
    "o v1 do forja não mixa",
)

PROVIDER_RE = re.compile(r"padr[aã]o[^\n]{0,60}\bfiles\b", re.IGNORECASE)

SPEECH_WORDS = ("fala", "narra", "diálogo", "dialogo", "musica", "música")


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _norm(line: str) -> str:
    return " ".join(line.strip().lower().split())


def _units(text: str) -> list:
    units = []  # type: list
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        units.append(line)
        for part in re.split(r"[.!?;]+", line):
            chunk = part.strip(" \t-–—*•")
            if chunk:
                units.append(chunk)
    return units


def _has_sfx_only_policy(text: str) -> bool:
    low = text.lower()
    if "ambiente" not in low:
        return False
    for unit in _units(text):
        ul = unit.lower()
        if "sfx" not in ul:
            continue
        if not re.search(r"\bsem\b", ul):
            continue
        if not any(k in ul for k in SPEECH_WORDS):
            continue
        if "não mixa" in ul or "sem áudio do clipe" in ul:
            continue
        if "não use o áudio embutido" in ul:
            continue
        return True
    return False


def _has_embedded_enters_and_mute(text: str) -> bool:
    low = text.lower()
    enters = ("entra no bed" in low or "entra por padrão" in low or "entra por padrao" in low)
    return enters and ("mode" in low and "mute" in low)


def _has_original_audio_exception(text: str) -> bool:
    low = text.lower()
    return "áudio original" in low and "dublagem" in low


def _flow_section(html_text: str) -> str:
    match = re.search(r'<section\s+id="flow".*?</section>', html_text, re.S | re.I)
    return match.group(0) if match else ""


def _quickstart_snippet(html_text: str) -> str:
    idx = html_text.find("Escolha as vozes")
    if idx < 0:
        return ""
    end = html_text.find("</li>", idx)
    if end < 0:
        return html_text[idx:idx + 1500]
    return html_text[idx:end]


def _fresh_build(tmp_path: Path, name: str) -> str:
    out = tmp_path / name
    proc = subprocess.run(
        [sys.executable, "-I", str(ROOT / "scripts" / "build-doc.py"), "--out", str(out)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return out.read_bytes().decode("utf-8")


# ---------------------------------------------------------------- M4: provider padrao


def test_env_example_does_not_claim_files_as_default():
    text = _read(".env.example")
    assert not PROVIDER_RE.search(text), "M4: .env.example ainda diz que o padrao e files"


def test_kit_sh_does_not_claim_files_as_default():
    text = _read("kit.sh")
    assert not PROVIDER_RE.search(text), "M4: kit.sh ainda diz que o padrao e o provider files"


def test_kit_ps1_does_not_claim_files_as_default():
    text = _read("kit.ps1")
    assert not PROVIDER_RE.search(text), "M4: kit.ps1 ainda diz que o padrao e o provider files"


def test_env_example_mentions_google_ai_studio():
    assert "google_ai_studio" in _read(".env.example"), "M4: .env.example nao menciona google_ai_studio"


def test_kit_sh_mentions_google_ai_studio():
    assert "google_ai_studio" in _read("kit.sh"), "M4: kit.sh nao menciona google_ai_studio"


def test_kit_ps1_mentions_google_ai_studio():
    assert "google_ai_studio" in _read("kit.ps1"), "M4: kit.ps1 nao menciona google_ai_studio"


# ------------------------------------------------- M3: frases erradas prosa


@pytest.mark.parametrize(
    "rel",
    ["prompts/14-google-flow-cenas.md", "README.md", "docs/index.html"],
)
def test_no_wrong_audio_claim(rel: str):
    text = _read(rel).lower()
    for phrase in WRONG_PHRASES:
        assert phrase not in text, "%s ainda contem a frase errada %r" % (rel, phrase)


def test_build_doc_source_has_no_wrong_audio_claim():
    # Fonte do guia: se continuar errada, docs==fresco nunca fecha apos a correcao.
    text = _read("scripts/build-doc.py").lower()
    for phrase in WRONG_PHRASES:
        assert phrase not in text, "scripts/build-doc.py ainda contem %r" % (phrase,)


# --------------------------------------- M3 + decisao do dono: prompt 14


def test_prompt14_asks_for_sfx_only_without_speech():
    text = _read("prompts/14-google-flow-cenas.md")
    assert _has_sfx_only_policy(text), (
        "M3/decisao: prompt 14 nao instrui SFX+ambiente sem fala/narracao/dialogo/musica "
        "na mesma frase/bullet (precisa de 'SFX' + 'sem' + fala/narracao/dialogo/musica e 'ambiente')"
    )


def test_prompt14_says_embedded_audio_enters_bed_and_mute_removes():
    # Continua funcionando hoje: o take entra no bed por padrao.
    text = _read("prompts/14-google-flow-cenas.md")
    assert _has_embedded_enters_and_mute(text), "prompt 14 deveria dizer que entra no bed e que mode: mute remove"


def test_prompt14_covers_original_audio_exception():
    text = _read("prompts/14-google-flow-cenas.md")
    assert _has_original_audio_exception(text), (
        "decisao do dono: prompt 14 nao traz a excecao do 'áudio original' com 'dublagem'"
    )


# ------------------------------------------------- M3: secao 04 do guia


def test_guide_flow_section_has_no_wrong_audio_claim():
    section = _flow_section(_read("docs/index.html"))
    assert section, "guia sem <section id=\"flow\">"
    low = section.lower()
    for phrase in WRONG_PHRASES:
        assert phrase not in low, "secao 04 do guia ainda contem %r" % (phrase,)


def test_guide_flow_section_repeats_sfx_only_policy():
    section = _flow_section(_read("docs/index.html"))
    assert section, "guia sem <section id=\"flow\">"
    assert _has_sfx_only_policy(section), "secao 04 nao repete SFX+ambiente sem fala/narracao/dialogo/musica"


def test_guide_flow_section_repeats_embedded_audio_rule():
    section = _flow_section(_read("docs/index.html"))
    assert section, "guia sem <section id=\"flow\">"
    assert _has_embedded_enters_and_mute(section), "secao 04 nao diz que entra no bed e que mode: mute remove"


def test_guide_flow_section_repeats_original_audio_exception():
    section = _flow_section(_read("docs/index.html"))
    assert section, "guia sem <section id=\"flow\">"
    assert _has_original_audio_exception(section), "secao 04 nao traz 'áudio original' + 'dublagem'"


# ---------------------------------------------------------------- L4: prompt 08


def test_prompt08_has_no_identical_lines():
    # Continua funcionando: hoje nao ha linha identica apos normalizar.
    text = _read("prompts/08-video-por-cenas.md")
    seen = {}  # type: dict
    for raw in text.splitlines():
        key = _norm(raw)
        if not key:
            continue
        assert key not in seen, "prompt 08 repete a linha %r" % (raw.strip()[:80],)
        seen[key] = True


def test_prompt08_has_no_duplicate_anchor_bullets():
    text = _read("prompts/08-video-por-cenas.md")
    count = 0
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped.startswith(("-", "*")):
            continue
        content = re.sub(r"^[-*•\s]+", "", stripped).lower()
        content = " ".join(content.split())
        if content.startswith("âncoras por palavra") or content.startswith("ancoras por palavra"):
            count += 1
    assert count <= 1, "L4: prompt 08 repete o bullet 'Âncoras por palavra' (%d vezes)" % count


# ---------------------------------------------------------------- L1: quickstart


def test_quickstart_mentions_google_ai_studio_before_piper():
    snippet = _quickstart_snippet(_read("docs/index.html"))
    assert snippet, "guia sem o passo 'Escolha as vozes'"
    low = snippet.lower()
    assert "google_ai_studio" in low, "L1: quickstart nao menciona google_ai_studio"
    assert "piper" in low, "quickstart sem piper"
    assert low.index("google_ai_studio") < low.index("piper"), "L1: piper aparece antes de google_ai_studio"


def test_quickstart_describes_piper_as_optional_offline():
    snippet = _quickstart_snippet(_read("docs/index.html"))
    assert snippet, "guia sem o passo 'Escolha as vozes'"
    low = snippet.lower()
    assert "piper" in low, "quickstart sem piper"
    assert "offline" in low, "L1: piper nao e descrito como alternativa offline"
    assert ("opcional" in low or "alternativa" in low or "plano b" in low), (
        "L1: piper nao e descrito como alternativa opcional (sem padrao)"
    )


def test_build_doc_quickstart_matches_guide_order():
    # Fonte e guia devem concordar; senao docs==fresco quebra apos a correcao.
    snippet = _quickstart_snippet(_read("scripts/build-doc.py"))
    assert snippet, "build-doc.py sem o passo 'Escolha as vozes'"
    low = snippet.lower()
    assert "google_ai_studio" in low and "piper" in low
    assert low.index("google_ai_studio") < low.index("piper")


# --------------------------------------- guia == build-doc + determinismo


def test_guide_matches_fresh_build_doc_output(tmp_path: Path):
    # Continua funcionando hoje: o guia versionado ja e igual ao fresco.
    fresh = _fresh_build(tmp_path, "guia.html")
    versioned = (ROOT / "docs" / "index.html").read_bytes().decode("utf-8")
    assert versioned == fresh, "docs/index.html difere da saida fresca do build-doc.py"


def test_build_doc_is_deterministic(tmp_path: Path):
    # Continua funcionando hoje.
    assert _fresh_build(tmp_path, "a.html") == _fresh_build(tmp_path, "b.html")


# ------------------------------------------------- next_actions sem envelope


@pytest.mark.parametrize(
    "rel",
    ["README.md", "docs/index.html", "scripts/build-doc.py"],
)
def test_no_doc_claims_next_actions_without_envelope(rel: str):
    # Continua funcionando: hoje ninguem afirma "sem envelope".
    low = _read(rel).lower()
    if "next_actions" not in low:
        return
    for bad in ("sem envelope", "fora do envelope", "sem o envelope"):
        assert bad not in low, "%s afirma next_actions %s" % (rel, bad)


def test_no_prompt_claims_next_actions_without_envelope():
    for path in sorted((ROOT / "prompts").glob("*.md")):
        low = path.read_text(encoding="utf-8").lower()
        if "next_actions" not in low:
            continue
        for bad in ("sem envelope", "fora do envelope", "sem o envelope"):
            assert bad not in low, "%s afirma next_actions %s" % (path.name, bad)


# ---------------------------------------------------------------- bordas


def test_normalize_handles_empty_and_whitespace():
    assert _norm("") == ""
    assert _norm("   ") == ""
    assert _norm("  A  B\tC ") == "a b c"


def test_flow_section_returns_empty_when_missing():
    assert _flow_section("<html><body>sem secao</body></html>") == ""


def test_quickstart_snippet_returns_empty_when_marker_missing():
    assert _quickstart_snippet("<html><body>sem passo</body></html>") == ""


def test_sfx_policy_rejects_empty_text():
    assert not _has_sfx_only_policy("")
    assert not _has_embedded_enters_and_mute("")
    assert not _has_original_audio_exception("")
