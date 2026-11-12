"""Workflow `post`: onze passos do brief humano a entrega empacotada.

O agente escreve JSON em `work/`; os passos de codigo validam, verificam o
hash do template, compoem, renderizam, medem e empacotam. A aprovacao e o
unico passo humano: `human_gates` so confere a evidencia gravada.
"""
from __future__ import annotations

from pathlib import Path

from ..steps import Step
from . import WORKFLOWS, register_workflow
from .human_gates import run_approve, run_review
from .post_brief import run_brief
from .post_compose import run_compose, run_template
from .post_content import run_copy, run_research
from .post_inspect import run_inspect
from .post_kit import run_lint, run_render

_PDF = {"a4", "a5", "pdf-a4-a5"}


def _brand(ctx) -> str:
    value = (ctx.cfg or {}).get("brand_id")
    return value.strip() if isinstance(value, str) else ""


def _piece(ctx) -> str:
    value = (ctx.cfg or {}).get("piece")
    return value.strip() if isinstance(value, str) and value.strip() else "post"


def _suffix(ctx) -> str:
    value = str((ctx.cfg or {}).get("format") or "").strip().lower()
    if value in _PDF or "pdf" in value:
        return ".pdf"
    return ".jpg" if "jpeg" in value or "jpg" in value else ".png"


def _work(ctx, sub, suffix) -> Path:
    return Path(ctx.work) / sub / (_piece(ctx) + suffix)


def _template(ctx) -> Path:
    return Path(ctx.root) / "brands" / _brand(ctx) / "templates"


def _run_deliver(ctx):
    """Delega o empacotamento ao modulo da lane de entrega."""
    from .post_deliver import run_deliver
    return run_deliver(ctx)


def steps_factory():
    return [
        Step("brief", "Valida o brief humano e grava work/brief.json.",
             lambda c: ([Path(c.root) / "brief.yaml"], {}),
             lambda c: [Path(c.work) / "brief.json"], run_brief, []),
        Step("research", "Valida a pesquisa com fonte e grava work/research.json.",
             lambda c: ([Path(c.work) / "brief.json"], {}),
             lambda c: [Path(c.work) / "research.json"], run_research, ["brief"]),
        Step("copy", "Mede o copy contra o formato e grava work/copy.json.",
             lambda c: ([Path(c.work) / "brief.json",
                         Path(c.work) / "research.json"], {}),
             lambda c: [Path(c.work) / "copy.json"], run_copy, ["research"]),
        Step("template", "Verifica o hash do template e grava work/template.json.",
             lambda c: ([_template(c) / "manifest.json",
                         _template(c) / (_piece(c) + ".html")], {}),
             lambda c: [Path(c.work) / "template.json"], run_template, []),
        Step("compose", "Preenche o template e grava work/compose/<peca>.html.",
             lambda c: ([Path(c.work) / "copy.json",
                         Path(c.work) / "assets.json",
                         Path(c.work) / "template.json",
                         _template(c) / "manifest.json"], {}),
             lambda c: [_work(c, "compose", ".html")], run_compose,
             ["copy", "template"]),
        Step("render", "Renderiza o HTML composto com o kit fixo.",
             lambda c: ([_work(c, "compose", ".html"),
                         Path(c.work) / "template.json"], {}),
             lambda c: [_work(c, "render", _suffix(c))], run_render, ["compose"]),
        Step("lint", "Roda o preflight do kit e grava work/lint/<peca>.json.",
             lambda c: ([_work(c, "compose", ".html")], {}),
             lambda c: [_work(c, "lint", ".json")], run_lint, ["compose"]),
        Step("inspect", "Mede dimensoes, contraste e dedup da arte.",
             lambda c: ([_work(c, "render", _suffix(c)),
                         _work(c, "lint", ".json")], {}),
             lambda c: [_work(c, "inspect", ".json")], run_inspect,
             ["lint", "render"]),
        Step("review", "Confere a revisao humana e registra a decisao.",
             lambda c: ([_work(c, "inspect", ".json")], {}),
             lambda c: [_work(c, "review", ".json")], run_review, ["inspect"]),
        Step("approve", "Confere approvals.json contra o hash da arte.",
             lambda c: ([Path(c.root) / "approvals.json",
                         _work(c, "review", ".json"),
                         _work(c, "render", _suffix(c))], {}),
             lambda c: [Path(c.work) / "approve.json"], run_approve, ["review"]),
        Step("deliver", "Empacota a arte aprovada em out/<peca>/.",
             lambda c: ([Path(c.work) / "approve.json",
                         Path(c.work) / "copy.json",
                         _work(c, "render", _suffix(c)),
                         Path(c.root) / "approvals.json"], {}),
             lambda c: [Path(c.out) / _piece(c) / "manifest.json"],
             _run_deliver, ["approve"]),
    ]


FILES = {
    "agent_writes": ["brief.yaml", "work/research.json", "work/copy.json",
                     "work/assets.json", "work/review/<peca>.json",
                     "approvals.json", "config.yaml"],
    "generated": ["work/", "out/<peca>/"],
}

if "post" not in WORKFLOWS:
    register_workflow(
        "post",
        "Peca digital unica: brief, pesquisa, copy, template, render, QA e entrega.",
        steps_factory,
        FILES,
    )
