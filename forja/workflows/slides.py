"""Workflow `slides`: deck YAML validado, composto, aprovado e empacotado.

O `deck` normaliza `deck.yaml`; os demais passos consomem `work/deck/` e
recebem ferramentas externas por `run=`.
"""
from __future__ import annotations

import hashlib
import json
import re, subprocess
import zipfile
from pathlib import Path

import yaml

from ..errors import ForjaError
from ..steps import Step
from . import WORKFLOWS, register_workflow

_DECK_KEYS = {"template", "template_sha256", "brand", "variant", "size", "locale",
              "notas", "modelo_catalogo"}
_SLIDE_KEYS = {"modelo", "titulo", "subtitulo", "corpo", "numero", "legenda",
               "rodape", "citacao", "atribuicao", "imagem", "imagem_sha256", "notas"}
_HEX = re.compile(r"[0-9a-fA-F]{64}\Z")

def _fail(code, msg, **details):
    return ForjaError(code, msg, details=details or None)

def _sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _read_json(path, code="MISSING_INPUT") -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _fail(code, "JSON ilegivel: %s" % path) from exc
    if not isinstance(data, dict): raise _fail(code, "JSON deve ser objeto: %s" % path)
    return data

def _write_json(path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    space = path.with_name(path.name + ".tmp")
    space.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    space.replace(path)

def _yaml(path, code):
    try: return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise _fail(code, "YAML ilegivel: %s" % Path(path).name) from exc

def _p(ctx, *parts):
    return Path(ctx.work).joinpath("deck", *parts)

def _out(ctx, suffix):
    project = (ctx.cfg or {}).get("project")
    name = project.get("name") if isinstance(project, dict) else None
    name = name.strip() if isinstance(name, str) and name.strip() else "deck"
    return Path(ctx.out) / (name + suffix)

def _check_slide(item, root) -> None:
    if not isinstance(item, dict) or set(item) - _SLIDE_KEYS: raise _fail("DECK_SCHEMA", "slides[] invalido")
    if not isinstance(item.get("modelo"), str) or not item["modelo"].strip(): raise _fail("DECK_SCHEMA", "modelo invalido")
    if "imagem" not in item:
        if "imagem_sha256" in item: raise _fail("DECK_SCHEMA", "imagem_sha256 sem imagem")
        return
    image = item["imagem"]
    relative = Path(image) if isinstance(image, str) else None
    expected = item.get("imagem_sha256")
    if not isinstance(expected, str) or not _HEX.fullmatch(expected):
        raise _fail("ASSET_HASH_MISMATCH", "imagem sem imagem_sha256 valido")
    if (relative is None or not image.strip() or relative.is_absolute()
            or ".." in relative.parts):
        raise _fail("ASSET_MISSING", "slides[].imagem invalida")
    source = Path(root) / relative
    if not source.is_file():
        raise _fail("ASSET_MISSING", "imagem ausente: %s" % source)
    if _sha256(source) != expected.lower():
        raise _fail("ASSET_HASH_MISMATCH", "sha256 da imagem nao confere")

def _variant(root, deck) -> str:
    manifest = _read_json(Path(root) / "brands" / deck["brand"] / "manifest.json",
                          "CONFIG_INVALID")
    names = [item for item in manifest.get("variants") or []
             if isinstance(item, str) and item.strip()]
    variant = deck.get("variant")
    if variant:
        if variant in names:
            return variant
        raise _fail("CONFIG_INVALID", "deck.variant fora do manifest: %r" % (variant,))
    if len(names) > 1:
        raise _fail("BRAND_VARIANT_REQUIRED",
                    "deck.variant obrigatorio: a marca tem mais de uma variante")
    if not names:
        raise _fail("CONFIG_INVALID", "manifest sem variants")
    return manifest.get("default_variant") or names[0]

def _run_deck(ctx):
    """Valida deck.yaml e grava o deck normalizado em work/deck/deck.json."""
    data = _yaml(Path(ctx.root) / "deck.yaml", "DECK_SCHEMA")
    if not isinstance(data, dict) or set(data) != {"schema", "deck", "slides"}:
        raise _fail("DECK_SCHEMA", "deck.yaml deve ter schema, deck e slides")
    if data.get("schema") != "forja-deck/v1":
        raise _fail("DECK_SCHEMA", "schema deve ser forja-deck/v1")
    deck = data.get("deck")
    if not isinstance(deck, dict) or set(deck) - _DECK_KEYS:
        raise _fail("DECK_SCHEMA", "deck tem chave desconhecida")
    if _DECK_KEYS - {"variant"} - set(deck):
        raise _fail("DECK_SCHEMA", "deck sem chave obrigatoria")
    if deck.get("size") != "13.333x7.5in":
        raise _fail("DECK_SCHEMA", "deck.size deve ser 13.333x7.5in")
    slides = data.get("slides")
    if not isinstance(slides, list) or not 3 <= len(slides) <= 40:
        raise _fail("DECK_SCHEMA", "slides deve ter de 3 a 40 itens")
    for item in slides:
        _check_slide(item, ctx.root)
    deck["variant"] = _variant(ctx.root, deck)
    _write_json(_p(ctx, "deck.json"), data)
    return {"ok": True, "slides": len(slides), "variant": deck["variant"]}

def _run_brief(ctx):
    _write_json(_p(ctx, "brief.json"), _yaml(Path(ctx.root) / "brief.yaml", "BRIEF_INCOMPLETE")); return {"ok": True}

def _run_assets(ctx):
    _write_json(_p(ctx, "assets.json"), {"assets": _read_json(_p(ctx, "brief.json")).get("assets") or {}}); return {"ok": True}

def _run_template(ctx):
    deck = _read_json(_p(ctx, "deck.json")).get("deck") or {}
    entry = next((t for t in _read_json(Path(ctx.root) / deck.get("modelo_catalogo", ""), "CONFIG_INVALID").get("templates") or [] if t.get("template_id") == deck.get("template")), None)
    path = Path(ctx.root) / entry["file"] if entry and entry.get("file") else None
    if path is None or not path.is_file(): raise _fail("DECK_TEMPLATE_MISSING", "template ausente")
    actual = _sha256(path)
    if actual != entry.get("sha256") or actual != deck.get("template_sha256"): raise _fail("TEMPLATE_HASH_MISMATCH", "sha256 nao confere")
    _write_json(_p(ctx, "template.json"), {"path": str(path), "sha256": actual}); return {"ok": True}

def _run_compose(ctx):
    _write_json(_p(ctx, "compose.json"), _read_json(_p(ctx, "deck.json"))); return {"ok": True}

def _run_pptx(ctx, *, run=subprocess.run):
    from pptx import Presentation
    compose = _read_json(_p(ctx, "compose.json"))
    prs = Presentation(_read_json(_p(ctx, "template.json"))["path"])
    for item in compose.get("slides") or []:
        slide = prs.slides.add_slide(prs.slide_layouts[-1])
        slide.shapes.add_textbox(0, 0, prs.slide_width, prs.slide_height).text_frame.text = item.get("titulo") or item["modelo"]
    target = _out(ctx, ".pptx"); prs.save(str(target)); return {"ok": True, "output": str(target)}

def _run_pdf(ctx, *, run=subprocess.run):
    source, target = _out(ctx, ".pptx"), _out(ctx, ".pdf")
    if not source.is_file(): raise _fail("MISSING_INPUT", "pptx ausente")
    try: result = run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(ctx.out), str(source)], cwd=str(ctx.root), capture_output=True, text=True)
    except OSError as exc: raise _fail("MISSING_PREREQ", "soffice nao encontrado") from exc
    if getattr(result, "returncode", 1) or not target.is_file(): raise _fail("DECK_CONVERT_FAILED", "PDF nao gerado")
    return {"ok": True, "output": str(target)}

def _run_inspect(ctx, *, run=subprocess.run):
    deck, pdf = _out(ctx, ".pptx"), _out(ctx, ".pdf")
    if not deck.is_file() or not pdf.is_file(): raise _fail("MISSING_INPUT", "pptx e pdf ausentes")
    try: output = run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    except (OSError, AttributeError) as exc: raise _fail("MISSING_PREREQ", "pdfinfo nao encontrado") from exc
    pages = next((line.split(":", 1)[1].strip() for line in output.splitlines() if line.startswith("Pages:")), "")
    data = {"ok": pages.isdigit(), "pptx": _sha256(deck), "pdf": _sha256(pdf), "pages": pages}
    _write_json(_p(ctx, "inspect.json"), data)
    if not data["ok"]: raise _fail("GATE_FAILED", "inspect sem paginas")
    return data

def _run_review(ctx):
    data = _read_json(_p(ctx, "review.json"), "GATE_FAILED")
    if data.get("decisao") not in ("aprovado", "ajustes"): raise _fail("GATE_FAILED", "decisao invalida")
    return {"ok": True}

def _run_approve(ctx):
    data = _read_json(Path(ctx.root) / "approvals.json", "APPROVAL_STALE")
    artifacts = data.get("artifacts") or []
    if data.get("schema_version") != 2 or not artifacts: raise _fail("APPROVAL_STALE", "approvals.json invalido")
    for item in artifacts:
        path = Path(ctx.root) / str(item.get("path", ""))
        if not path.is_file() or _sha256(path) != item.get("sha256"): raise _fail("APPROVAL_STALE", "artefato ausente ou mudou")
    if not {str(_out(ctx, ".pptx")), str(_out(ctx, ".pdf"))} <= {str(Path(ctx.root) / str(i.get("path"))) for i in artifacts}: raise _fail("APPROVAL_STALE", "aprovacao incompleta")
    return {"ok": True}

def _run_deliver(ctx):
    files = [_out(ctx, ".pptx"), _out(ctx, ".pdf"), _p(ctx, "deck.json")]
    if any(not path.is_file() for path in files): raise _fail("ASSET_MISSING", "pacote incompleto")
    target = _out(ctx, ".zip")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as package:
        for path in files: package.write(path, path.name)
    return {"ok": True, "output": str(target)}

def _paths(ctx, target):
    where, name = target
    return [Path(ctx.root) / name] if where == "root" else [_out(ctx, name)] if where == "out" else [_p(ctx, name)]

_SPECS = [
    ("brief", "Valida o brief humano e grava work/deck/brief.json.", _run_brief, [], ("work", "brief.json")),
    ("assets", "Indexa os ativos do brief em work/deck/assets.json.", _run_assets, ["brief"], ("work", "assets.json")),
    ("deck", "Valida deck.yaml (forja-deck/v1) e normaliza o deck.", _run_deck, ["brief", "assets"], ("work", "deck.json")),
    ("template", "Confere o sha256 do template contra o catalogo.", _run_template, ["deck"], ("work", "template.json")),
    ("compose", "Resolve modelos e imagens em work/deck/compose.json.", _run_compose, ["template"], ("work", "compose.json")),
    ("pptx", "Monta o .pptx a partir do template e do compose.", _run_pptx, ["compose"], ("out", ".pptx")),
    ("pdf", "Converte o .pptx para PDF com o LibreOffice.", _run_pdf, ["pptx"], ("out", ".pdf")),
    ("inspect", "Mede o PDF e grava work/deck/inspect.json.", _run_inspect, ["pdf"], ("work", "inspect.json")),
    ("review", "Portao humano: confere a decisao de review.", _run_review, ["inspect"], ("work", "review.json")),
    ("approve", "Confere approvals.json contra pptx e pdf.", _run_approve, ["review"], ("root", "approvals.json")),
    ("deliver", "Empacota pptx, pdf e deck aprovados em out/.", _run_deliver, ["approve"], ("out", ".zip")),
]

def _inputs(ctx):
    return ([Path(ctx.root) / "deck.yaml", Path(ctx.root) / "approvals.json"], {})

def steps_factory():
    return [Step(name, doc, _inputs, lambda c, t=target: _paths(c, t), run, needs)
            for name, doc, run, needs, target in _SPECS]

FILES = {"agent_writes": ["deck.yaml", "brief.yaml", "approvals.json", "config.yaml"],
         "generated": ["work/deck/", "out/"]}

if "slides" not in WORKFLOWS:
    register_workflow("slides", "Deck PPTX: brief, deck, template, PDF e entrega.",
                      steps_factory, FILES)
