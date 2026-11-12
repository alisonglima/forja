"""Aceitacao ESTATICA das provas L-PROVA-KIT-01..06 (escrito pelo orquestrador).

Os scripts .mjs so funcionam de verdade dentro do LXC, com o open-design-agent-kit,
Chrome e ffmpeg: isso e a fase de execucao (evidencias lidas pelos testes
`test_dimensoes`, `test_pdf_rgb`, ...). Aqui a lane so prova o que pode provar
sem LXC: sintaxe, interface, seguranca e `--dry-run` sem processos externos.

Interface comum de cada script:
  node scripts/prova-kit/<nome>.mjs --out DIR [--dry-run] [--help]
  --help       uso (cita --out), exit 0
  sem --out    exit 2 e mensagem no stderr
  --dry-run    imprime no stdout um JSON {"script", "evidencia", "workspace", "sidecars",
               "comandos": [...]} ("evidencia" = nome da pasta p5-0N-..., "comandos" =
               lista nao vazia de strings), NAO inicia nenhum processo externo e NAO
               cria arquivos fora de DIR.
Contrato do kit (docs/prova-kit/cli-0.4.0.md, lido da FONTE): todo artefato exportado/
checado precisa de sidecar `<entry>.artifact.json` e ficar DENTRO do workspace; por isso
"workspace" = caminho relativo a DIR, "sidecars" = lista de `*.artifact.json` previstos
(vazia so em video-compare, que usa render-video) e todo comando do kit leva --workspace.
"""
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PASTA = ROOT / "scripts" / "prova-kit"
SCRIPTS = {
    "export-exato.mjs": "p5-01-dimensoes",
    "export-pdf.mjs": "p5-02-pdf",
    "preflight-provocado.mjs": "p5-03-preflight",
    "lote-csv.mjs": "p5-04-lote",
    "video-compare.mjs": "p5-05-video",
    "medir-rede.mjs": "p5-06-rede",
}
PROIBIDO = re.compile(r"\b(ssh|scp|rsync|sshpass|pct|qm|pvesh)\b|shell\s*:\s*true|\beval\s*\(|new\s+Function\s*\(")
# o kit 0.4.0 NAO le estas variaveis nem tem --version (cli-0.4.0.md secoes 1, 2 e 7)
INEXISTENTE = re.compile(r"OPEN_DESIGN_(OUTPUT_DIR|WORKSPACE_ROOT|DEFAULT_WORKSPACE|PREVIEW)\b|[\"'`\s]--version\b")
USAM_SIDECAR = {"export-exato.mjs", "export-pdf.mjs", "preflight-provocado.mjs", "lote-csv.mjs", "medir-rede.mjs"}
FERRAMENTAS = ("npx", "npm", "node-gyp", "identify", "convert", "magick", "pdftoppm", "pdftotext",
               "pdfinfo", "qpdf", "ffmpeg", "ffprobe", "google-chrome", "google-chrome-prova",
               "tcpdump", "ss", "curl", "wget", "apt-get")


def _caminho(nome):
    p = PASTA / nome
    assert p.is_file(), f"falta {p}"
    return p


def _falsos(tmp_path):
    """Ferramentas falsas no PATH: gravam a chamada e falham (dry-run nao pode chamar nenhuma)."""
    bindir, marca = tmp_path / "bin", tmp_path / "chamadas.log"
    bindir.mkdir()
    for nome in FERRAMENTAS:
        f = bindir / nome
        f.write_text(f'#!/bin/sh\necho "{nome} $*" >> "{marca}"\nexit 99\n', encoding="utf-8")
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return bindir, marca


def _node(tmp_path, nome, *args):
    bindir, marca = _falsos(tmp_path)
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}")
    proc = subprocess.run(["node", str(_caminho(nome)), *args], capture_output=True, text=True,
                          env=env, cwd=tmp_path, timeout=60)
    return proc, marca


@pytest.mark.parametrize("nome", SCRIPTS)
def test_sintaxe_node(nome):
    proc = subprocess.run(["node", "--check", str(_caminho(nome))], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("nome", SCRIPTS)
def test_sem_palavras_proibidas(nome):
    txt = _caminho(nome).read_text(encoding="utf-8")
    achados = sorted({m.group(0) for m in PROIBIDO.finditer(txt)})
    assert not achados, f"{nome}: proibido no script: {achados}"


@pytest.mark.parametrize("nome", SCRIPTS)
def test_help_cita_out(nome, tmp_path):
    proc, marca = _node(tmp_path, nome, "--help")
    assert proc.returncode == 0, proc.stderr
    assert "--out" in (proc.stdout + proc.stderr)
    assert not marca.exists()


@pytest.mark.parametrize("nome", SCRIPTS)
def test_sem_out_falha_com_exit_2(nome, tmp_path):
    proc, marca = _node(tmp_path, nome)
    assert proc.returncode == 2, (proc.returncode, proc.stderr)
    assert "--out" in proc.stderr and not marca.exists()


@pytest.mark.parametrize("nome,pasta", SCRIPTS.items())
def test_dry_run_plano_sem_processos(nome, pasta, tmp_path):
    saida = tmp_path / "saida"
    proc, marca = _node(tmp_path, nome, "--out", str(saida), "--dry-run")
    assert proc.returncode == 0, proc.stderr
    assert not marca.exists(), f"dry-run chamou ferramenta externa: {marca.read_text()}"
    plano = json.loads(proc.stdout)
    assert plano["script"].endswith(nome) and plano["evidencia"] == pasta
    assert isinstance(plano["comandos"], list) and plano["comandos"]
    assert all(isinstance(c, str) and c.strip() for c in plano["comandos"])
    fora = [p for p in tmp_path.iterdir() if p.name not in ("bin", "saida", "chamadas.log")]
    assert not fora, f"dry-run criou arquivos fora de --out: {fora}"


@pytest.mark.parametrize("nome", SCRIPTS)
def test_sem_suposicoes_refutadas_pela_fonte(nome):
    txt = _caminho(nome).read_text(encoding="utf-8")
    achados = sorted({m.group(0).strip() for m in INEXISTENTE.finditer(txt)})
    assert not achados, f"{nome}: o kit 0.4.0 nao tem/le isto (cli-0.4.0.md): {achados}"


@pytest.mark.parametrize("nome,pasta", SCRIPTS.items())
def test_dry_run_declara_workspace_e_sidecars(nome, pasta, tmp_path):
    proc, marca = _node(tmp_path, nome, "--out", str(tmp_path / "saida"), "--dry-run")
    assert proc.returncode == 0, proc.stderr
    plano = json.loads(proc.stdout)
    assert isinstance(plano.get("workspace"), str) and plano["workspace"].strip()
    assert not os.path.isabs(plano["workspace"]), "workspace deve ser relativo a --out"
    side = plano.get("sidecars")
    assert isinstance(side, list)
    if nome in USAM_SIDECAR:
        assert side and all(isinstance(x, str) and x.endswith(".artifact.json") for x in side)
        kit = [c for c in plano["comandos"] if "open-design-agent-kit" in c]
        assert kit, "nenhum comando do kit no plano"
        assert all("--workspace" in c for c in kit), f"comando do kit sem --workspace: {kit}"
    else:
        assert side == []


def test_preflight_usa_fail_on_warning_em_todos_os_casos(tmp_path):
    """Run real: contraste e safe-area sao WARNING no kit (cli-0.4.0.md secao 5); com --fail-on error o exit fica 0
    e o plano espera 1. Todos os cinco casos usam --fail-on warning (o controle limpo continua 0)."""
    proc, marca = _node(tmp_path, "preflight-provocado.mjs", "--out", str(tmp_path / "saida"), "--dry-run")
    assert proc.returncode == 0, proc.stderr
    kit = [c for c in json.loads(proc.stdout)["comandos"] if "open-design-agent-kit" in c and " check " in c]
    assert len(kit) == 5, kit
    assert all("--fail-on warning" in c and "--fail-on error" not in c for c in kit), kit
