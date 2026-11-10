from __future__ import annotations

import os
import shutil
from pathlib import Path

from . import cache, config, errors

_DIRS = ("input", "voices", "work", "out")
_SOURCE_NAME = "source.mp4"


class Project:
    """Caminhos canonicos de um projeto forja."""

    def __init__(self, root):
        self.root = Path(root)
        self.config_path = self.root / "config.yaml"
        self.work = self.root / "work"
        self.out = self.root / "out"
        self.input = self.root / "input"

    def load_config(self) -> dict:
        return config.load_config(self.config_path)


class _Ctx:
    """Subconjunto de ``steps.Ctx`` suficiente para calcular hashes."""

    def __init__(self, project: Project, cfg: dict):
        self.root = project.root
        self.cfg = cfg
        self.work = project.work
        self.out = project.out
        self.env = os.environ
        self.log = _noop
        self.dry_run = False


def _noop(message) -> None:
    return None


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _project_section(cfg: dict) -> dict:
    section = cfg.get("project")
    return section if isinstance(section, dict) else {}


def _workflow_doc(workflow: str) -> str:
    if workflow == "storyboard":
        return "videos por cenas"
    if workflow == "dub":
        return "dublagem EN->pt-BR"
    return f"workflow {workflow}"


def agents_md(workflow) -> str:
    """Instrucoes em pt-BR para o agente que opera o projeto."""
    workflow = str(workflow)
    return (
        f"# Projeto forja ({workflow}: {_workflow_doc(workflow)})\n"
        "\n"
        "## Ciclo de trabalho\n"
        "\n"
        "1. Rode `forja --json status` para ver o estado e a proxima acao.\n"
        "2. Faca o proximo passo indicado (ou edite os arquivos que so voce escreve).\n"
        "3. Verifique com `forja --json status` e com o gate de QA antes de entregar.\n"
        "\n"
        "## Regras\n"
        "\n"
        "- Segredo so no ambiente: nunca grave chaves no projeto, em log ou no `--json`.\n"
        "- Nunca imprima o valor de uma chave; reporte apenas o nome da variavel.\n"
        "- Prefira sempre `--json` para ler a resposta da CLI de forma estavel.\n"
        "- Nao edite `work/`: ele e descartavel e gerado pelos passos.\n"
        "- Tempos em segundos (float), relativos ao inicio do clipe.\n"
        "- Rode o gate de QA antes de entregar o video.\n"
        "- Peca decisao humana para voz e consentimento antes de sintetizar fala.\n"
        "\n"
        "## Arquivos que o agente escreve\n"
        "\n"
        + _agent_files_md(workflow)
        + "- `config.yaml`: ajustes do projeto (sem segredos).\n"
    )


def _agent_files_md(workflow: str) -> str:
    if workflow == "storyboard":
        return (
            "- `storyboard.yaml`: cenas, camadas (clip, narration, captions, card, music), duracoes e licencas.\n"
            "- `assets/`: clipes, cards (PNG) e trilhas usados pelo storyboard (caminhos relativos a raiz).\n"
            "- `voices/<cena>.wav`: a narracao de cada cena, gerada por voce com a conta/ferramenta do usuario (provider `files`).\n"
        )
    return (
        "- `cues.json`: falas, papeis e textos em pt-BR.\n"
        "- `lower_thirds.json`: janelas de tarja de nome no original.\n"
        "- `voices/<id>.wav`: a voz de cada cue, gerada por voce com a conta/ferramenta do usuario (provider `files`).\n"
    )


STORYBOARD_STARTER = """# Storyboard (versao 1). Edite as cenas; rode `forja --json status` para ver o proximo passo.
# Camadas: clip, narration, captions, card, music (music exige license.kind). Caminhos relativos a raiz do projeto.
version: 1
canvas: {w: 1280, h: 720, fps: 30}
scenes:
  - id: abertura
    duration: {from: narration, pad_before: 0.4, pad_after: 0.5}
    layers:
      - {type: narration, text: "Escreva aqui a narracao da primeira cena."}
      - {type: captions, from: narration}
"""


def scaffold(root, name, source=None, workflow="dub", force=False) -> list[str]:
    """Cria o esqueleto de um projeto e devolve caminhos relativos."""
    root = Path(root)
    if root.exists() and not root.is_dir():
        raise errors.ForjaError("USAGE", f"caminho nao e um diretorio: {root}")
    if root.exists() and not force and any(root.iterdir()):
        raise errors.ForjaError(
            "USAGE",
            f"projeto ja existe: {root}",
            hint="use --force para recriar os arquivos do projeto",
        )

    root.mkdir(parents=True, exist_ok=True)
    created = []
    for dirname in _DIRS:
        directory = root / dirname
        directory.mkdir(parents=True, exist_ok=True)
        created.append(_relative(root, directory))

    config_path = root / "config.yaml"
    if config_path.exists():
        config_path.unlink()
    config.write_default_config(
        config_path,
        project={"name": str(name), "workflow": str(workflow)},
    )
    created.append(_relative(root, config_path))

    if workflow == "storyboard":
        (root / "assets").mkdir(parents=True, exist_ok=True)
        created.append("assets")
        path = root / "storyboard.yaml"
        _write_text(path, STORYBOARD_STARTER)
        created.append(_relative(root, path))
    else:
        for filename in ("cues.json", "lower_thirds.json"):
            path = root / filename
            _write_text(path, "[]\n")
            created.append(_relative(root, path))

    agents_path = root / "AGENTS.md"
    _write_text(agents_path, agents_md(workflow))
    created.append(_relative(root, agents_path))

    if source is not None:
        source_path = Path(source)
        if not source_path.is_file():
            raise errors.ForjaError(
                "MISSING_INPUT", f"video de entrada nao encontrado: {source_path}"
            )
        target = root / "input" / _SOURCE_NAME
        if source_path.resolve() != target.resolve():
            shutil.copy2(source_path, target)
        created.append(_relative(root, target))

    return created


def _step_state(entry, input_hash: str, outputs) -> tuple[str, str]:
    if entry is None:
        return "missing", "passo ainda nao executado (sem registro no manifesto)"
    if entry.get("input_hash") != input_hash:
        return "stale", "entradas mudaram desde a ultima execucao"
    missing = [Path(output) for output in outputs if not Path(output).exists()]
    if missing:
        return "missing", f"saida ausente: {missing[0].name}"
    return "fresh", "saidas atualizadas"


def status(project, steps) -> dict:
    """Estado dos passos e a proxima acao recomendada."""
    cfg = project.load_config()
    project_section = _project_section(cfg)
    name = project_section.get("name") or project.root.name
    workflow = str(project_section.get("workflow") or "dub")

    ctx = _Ctx(project, cfg)
    manifest = cache.Manifest(project.work / "manifest.json")
    entries = []
    next_action = None

    for step in steps:
        paths, extra = step.inputs(ctx)
        input_hash = cache.hash_inputs(paths, extra)
        outputs = step.outputs(ctx)
        state, reason = _step_state(manifest.get(step.name), input_hash, outputs)
        entries.append({"name": step.name, "state": state, "reason": reason})
        if next_action is None and state != "fresh":
            next_action = {
                "command": f"forja run --only {step.name}",
                "why": reason,
            }

    return {
        "project": str(name),
        "workflow": workflow,
        "steps": entries,
        "next": next_action,
    }
