"""Workflow lote-digital: artes em lote a partir de CSV/JSON (8 passos)."""
from __future__ import annotations

from pathlib import Path

from .. import kit, templates
from ..errors import ForjaError
from ..steps import Step
from . import WORKFLOWS, register_workflow
from .dub import _write_json


def _fail(code, msg, **details):
    return ForjaError(code, msg, details=details or None)


def _cfg(ctx):
    section = (ctx.cfg or {}).get("lote")
    return section if isinstance(section, dict) else {}


def _p(ctx, *parts):
    return Path(ctx.work).joinpath(*parts)


def _name(ctx, key):
    value = (ctx.cfg or {}).get(key)
    if not isinstance(value, str) or not value.strip():
        raise _fail("MISSING_INPUT", "config sem %s do lote" % key)
    return value.strip()


def _inputs(ctx):
    return ([Path(ctx.root) / _cfg(ctx).get("entrada", "lote.csv"),
             _p(ctx, "lote", "plano.json"), Path(ctx.root) / "config.yaml"],
            {"lote": _cfg(ctx)})


def _run_validate(ctx):
    from . import lote_validate
    return lote_validate.run_validate_data(
        Path(ctx.root) / _cfg(ctx).get("entrada", "lote.csv"),
        _p(ctx, "lote", "plano.json"), formatos=_cfg(ctx).get("formatos"))


def _run_template(ctx):
    brand, piece = _name(ctx, "brand_id"), _name(ctx, "piece")
    entry = templates.verify_template(Path(ctx.root) / "brands" / brand, piece)
    data = dict(entry, schema=1, brand=brand, template=piece)
    _write_json(_p(ctx, "lote", "template.json"), data)
    return {"ok": True, **data}


def _run_render(ctx):
    from . import lote_render
    artes = lote_render.run_render_lote(_p(ctx, "lote", "plano.json"),
                                        _p(ctx, "lote", "render"))
    return {"total": len(artes), "artes": artes}


def _run_lint(ctx):
    artes = [p for p in _p(ctx, "lote", "render").glob("*")
             if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".pdf")]
    if not artes:
        raise _fail("MISSING_INPUT", "nenhuma arte renderizada para o lint")
    checked = kit.check(str(sorted(artes)[0]), cwd=str(ctx.root))
    _write_json(_p(ctx, "lote", "lint.json"), checked)
    if not checked["ok"]:
        raise _fail("GATE_FAILED", "kit check reprovou a amostra do lote",
                    issues=checked["issues"])
    return checked


def _run_sample(ctx):
    from . import lote_sample
    return lote_sample.run_sample_check(
        _p(ctx, "lote", "plano.json"), _p(ctx, "lote", "render"),
        _p(ctx, "lote", "sample.json"))


def _gate(ctx, action):
    from . import human_gates
    return getattr(human_gates, action)(ctx, _name(ctx, "piece"))


def _run_deliver(ctx):
    from . import lote_deliver
    return lote_deliver.run_deliver_lote(
        _p(ctx, "lote", "render"), Path(ctx.root) / "approvals.json",
        Path(ctx.out) / "lote" / "lote.zip", agora=(ctx.cfg or {}).get("now"))


def _step(name, doc, run, needs, *out):
    return Step(name, doc, _inputs, lambda c: [_p(c, *out)], run, needs)


def steps_factory():
    return [
        _step("validate-data", "Valida CSV/JSON do lote e grava o plano.", _run_validate, [], "lote", "plano.json"),
        _step("template", "Confere o sha256 do template contra o manifesto.", _run_template, ["validate-data"], "lote", "template.json"),
        _step("render-lote", "Renderiza uma arte por linha com o kit fixo.", _run_render, ["template"], "lote", "render"),
        _step("lint-lote", "Roda o preflight do kit na amostra renderizada.", _run_lint, ["render-lote"], "lote", "lint.json"),
        _step("sample-check", "Confere contraste, dedup e QR da amostra.", _run_sample, ["lint-lote"], "lote", "sample.json"),
        _step("review", "Portao humano: registra a revisao da amostra.", lambda c: _gate(c, "run_review"), ["sample-check"], "review"),
        _step("approve", "Valida approvals.json contra as artes aprovadas.", lambda c: _gate(c, "run_approve"), ["review"], "approve.json"),
        Step("deliver", "Empacota o lote aprovado em out/lote/lote.zip.",
             _inputs, lambda c: [Path(c.out) / "lote" / "lote.zip"],
             _run_deliver, ["approve"]),
    ]


FILES = {
    "agent_writes": ["lote.csv", "config.yaml", "brief.yaml", "approvals.json"],
    "generated": ["work/lote/", "out/lote/"],
}

if "lote-digital" not in WORKFLOWS:
    register_workflow("lote-digital", "Artes em lote a partir de CSV/JSON, "
                      "com amostra, revisao e entrega.", steps_factory, FILES)
