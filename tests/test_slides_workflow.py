"""Contrato do workflow `slides` (T-SLIDES-01; plano:1824-1838, 1795-1820).
Congela: registro (1824); os 11 passos (1826-1838); arquivos de estado
(1795-1808); `deck.variant` obrigatorio com >1, ausente ->
`BRAND_VARIANT_REQUIRED`, fora -> `CONFIG_INVALID` (217,1692,1968); schema
`forja-deck/v1`, 3-40 slides (1686-1700); `imagem_sha256` com imagem (1698).
`deck` roda via `Step.run` (1824).
# DIVERGENCIA 1801 (`work/deck/<campanha>.json`) x 1830 (`work/deck/deck.json`):
# congela o passo (1830); caminho por campanha fica para o contrato de estado.
# LACUNA: schema de `variants.json` e de T-BRAND-VARIANTS-01 (aqui so ids); PNG
# 1280/360 do `inspect` sem caminho (1835 x 1805); chaves do deck normalizado
# nao fixadas (assume-se o YAML); `template_sha256` contra arquivo/indice nao
# exercitado; `FILES` segue `dub`.
"""

import base64
import json
from pathlib import Path

import pytest
import yaml

STEPS = ["brief", "assets", "deck", "template", "compose", "pptx", "pdf",
         "inspect", "review", "approve", "deliver"]
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
FIXED = {"brief": "work/deck/brief.json", "assets": "work/deck/assets.json",
         "deck": "work/deck/deck.json", "template": "work/deck/template.json",
         "compose": "work/deck/compose.json", "inspect": "work/deck/inspect.json",
         "review": "work/deck/review.json", "approve": "approvals.json"}

def _ctx(root):
    from forja.steps import Ctx
    return Ctx(root=root, cfg={"project": {"name": "campanha", "workflow": "slides"}},
               work=root / "work", out=root / "out", env={}, log=lambda msg: None,
               dry_run=False)
def _json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
def _brand(root, variants=("lions", "leo", "leo-lion")):
    brand = root / "brands" / "leo-lions"
    (brand / "decks").mkdir(parents=True)
    _json(brand / "manifest.json", {"brand_id": "leo-lions", "variants": list(variants),
          "default_variant": variants[0], "variants_file": "variants.json"})
    _json(brand / "variants.json", {"schema": "forja-brand-variants/v1",
          "variants": [{"id": item} for item in variants]})
    models = {n: {"slide": 1} for n in ("texto", "numeros", "fechamento", "imagem_texto")}
    _json(brand / "decks" / "modelos.json", {
        "schema": "forja-deck-models/v2", "brand": "leo-lions",
        "default_template_id": "lions-oficial-2022",
        "templates": [{"template_id": "lions-oficial-2022", "role": "base",
                       "optional": False, "compose": True, "file": "t.pptx",
                       "sha256": "0" * 64, "variants": ["lions", "leo-lion"]}],
        "models": models})
def _deck(variant="lions", image=False):
    slides = [{"modelo": "texto", "titulo": "O que fazemos",
               "corpo": ["Serviço", "Companheirismo", "Impacto"]},
              {"modelo": "numeros", "numero": "40%",
               "legenda": "dos associados em ações locais"},
              {"modelo": "fechamento", "titulo": "Obrigado",
               "rodape": "© 2026 Leo Clube de Exemplo"}]
    deck = {"schema": "forja-deck/v1", "deck": {
        "template": "lions-oficial-2022", "template_sha256": "0" * 64,
        "brand": "leo-lions", "size": "13.333x7.5in", "locale": "pt-BR",
        "notas": True, "modelo_catalogo": "brands/leo-lions/decks/modelos.json"}}
    if variant is not None:
        deck["deck"]["variant"] = variant
    if image is not False:
        slide = {"modelo": "imagem_texto", "titulo": "Visão 2027",
                 "corpo": ["Cada clube, um projeto."], "imagem": "assets/capa.png"}
        if image is not None:
            slide["imagem_sha256"] = image
        slides[0] = slide
    deck["slides"] = slides
    return deck
def _write(root, deck=None, raw=None):
    text = raw if raw is not None else yaml.safe_dump(deck, allow_unicode=True)
    (root / "deck.yaml").write_text(text, encoding="utf-8")
def _run_deck(root):
    from forja.workflows import slides
    step = {item.name: item for item in slides.steps_factory()}["deck"]
    return step.run(_ctx(root))

def test_workflow_registers_the_eleven_steps_and_state_paths(tmp_path):
    import forja.workflows.slides  # noqa: F401
    from forja.workflows import WORKFLOWS, slides
    workflow = WORKFLOWS["slides"]
    assert workflow.summary.strip()
    assert {"deck.yaml", "approvals.json"} <= set(workflow.files["agent_writes"])
    steps = slides.steps_factory()
    assert [step.name for step in steps] == STEPS
    assert all(step.doc.strip() and callable(step.run) for step in steps)
    assert all(callable(step.inputs) and callable(step.outputs) for step in steps)
    ctx = _ctx(tmp_path)
    outputs = {step.name: [Path(path) for path in step.outputs(ctx)]
               for step in steps}
    for name, relative in FIXED.items():
        assert outputs[name][0] == tmp_path / relative
    for name in ("pptx", "pdf"):
        assert outputs[name][0].parent == ctx.out
        assert outputs[name][0].suffix == "." + name
    assert outputs["deliver"][0].parent == ctx.out
def test_deck_step_writes_normalized_deck_with_variant(tmp_path):
    from forja.workflows import slides  # noqa: F401
    _brand(tmp_path)
    _write(tmp_path, _deck())
    _run_deck(tmp_path)
    deck = json.loads((tmp_path / "work/deck/deck.json").read_text(encoding="utf-8"))
    assert deck["deck"]["variant"] == "lions"
    assert deck["deck"]["size"] == "13.333x7.5in"
    assert [item["modelo"] for item in deck["slides"]] == [
        "texto", "numeros", "fechamento"]
@pytest.mark.parametrize("variant,code", [
    (None, "BRAND_VARIANT_REQUIRED"), ("leo-lions-2027", "CONFIG_INVALID")])
def test_deck_variant_is_closed_and_required(tmp_path, variant, code):
    from forja.errors import ForjaError
    from forja.workflows import slides  # noqa: F401
    _brand(tmp_path)
    _write(tmp_path, _deck(variant=variant))
    with pytest.raises(ForjaError) as excinfo:
        _run_deck(tmp_path)
    assert excinfo.value.code == code
@pytest.mark.parametrize("case", ["chave", "tamanho", "slides", "yaml"])
def test_deck_step_rejects_schema_violations(tmp_path, case):
    from forja.errors import ForjaError
    from forja.workflows import slides  # noqa: F401
    _brand(tmp_path)
    deck = _deck()
    if case == "chave":
        deck["deck"]["extra"] = "nao existe"
        _write(tmp_path, deck)
    elif case == "tamanho":
        deck["deck"]["size"] = "4x3in"
        _write(tmp_path, deck)
    elif case == "slides":
        deck["slides"] = deck["slides"][:2]
        _write(tmp_path, deck)
    else:
        _write(tmp_path, raw="schema: forja-deck/v1\ndeck: {template: [")
    with pytest.raises(ForjaError) as excinfo:
        _run_deck(tmp_path)
    assert excinfo.value.code == "DECK_SCHEMA"
@pytest.mark.parametrize("sha", [None, "f" * 64])
def test_image_without_matching_sha_is_asset_hash_mismatch(tmp_path, sha):
    from forja.errors import ForjaError
    from forja.workflows import slides  # noqa: F401
    _brand(tmp_path)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "capa.png").write_bytes(PNG)
    _write(tmp_path, _deck(image=sha))
    with pytest.raises(ForjaError) as excinfo:
        _run_deck(tmp_path)
    assert excinfo.value.code == "ASSET_HASH_MISMATCH"
