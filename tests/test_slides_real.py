"""Contrato deck REAL (T-SLIDES-REAL-01): compose+pptx do workflow slides."""
def _ctx(root):
    from forja.steps import Ctx
    return Ctx(root=root, cfg={"project": {"name": "campanha", "workflow": "slides"}}, work=root / "work", out=root / "out", env={}, log=lambda m: None, dry_run=False)
def _steps():
    from forja.workflows import slides
    return {s.name: s for s in slides.steps_factory()}
def _base(root):
    import hashlib, json
    import yaml
    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation()
    blank = prs.slide_layouts[6]
    s1 = prs.slides.add_slide(blank)
    a = s1.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1)); a.name = "Headline"; a.text_frame.text = "Headline here"
    b = s1.shapes.add_textbox(Inches(1), Inches(3), Inches(3), Inches(1)); b.name = "Subhead"; b.text_frame.text = "Subhead here"
    s2 = prs.slides.add_slide(blank)
    c = s2.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1)); c.name = "Text Placeholder 1"; c.text_frame.text = "Section here"
    s3 = prs.slides.add_slide(blank)
    d = s3.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1)); d.name = "Body Copy"; d.text_frame.text = "Body Copy A"
    e = s3.shapes.add_textbox(Inches(1), Inches(3), Inches(3), Inches(1)); e.name = "Body Copy"; e.text_frame.text = "Body Copy B"
    (root / "tpl.pptx").parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(root / "tpl.pptx"))
    sha = hashlib.sha256((root / "tpl.pptx").read_bytes()).hexdigest()
    bd = root / "brands" / "leo-lions" / "decks"; bd.mkdir(parents=True, exist_ok=True)
    (root / "brands" / "leo-lions" / "manifest.json").write_text(json.dumps({"brand_id": "leo-lions", "variants": ["lions", "leo", "leo-lion"], "default_variant": "lions", "variants_file": "variants.json"}), encoding="utf-8")
    (root / "brands" / "leo-lions" / "variants.json").write_text(json.dumps({"schema": "forja-brand-variants/v1", "variants": [{"id": v} for v in ("lions", "leo", "leo-lion")]}), encoding="utf-8")
    models = {"capa_foto": {"slide": 1, "suportado": True, "campos": {"titulo": {"shape": "Headline", "tipo": "texto"}, "subtitulo": {"shape": "Subhead", "tipo": "texto"}}}, "secao": {"slide": 2, "suportado": True, "campos": {"titulo": {"shape": "Text Placeholder 1", "tipo": "texto"}}}, "imagem_texto": {"slide": 3, "suportado": True, "campos": {"titulo": {"shape": "Body Copy", "contains": "Body Copy A", "tipo": "texto"}, "corpo": {"shape": "Body Copy", "contains": "Body Copy B", "tipo": "lista"}}}, "grafico": {"suportado": False, "campos": {}}}
    (bd / "modelos.json").write_text(json.dumps({"schema": "forja-deck-models/v2", "brand": "leo-lions", "default_template_id": "base", "templates": [{"template_id": "base", "role": "base", "optional": False, "compose": True, "file": "tpl.pptx", "sha256": sha, "variants": ["lions", "leo-lion"]}], "models": models}), encoding="utf-8")
    deck = {"schema": "forja-deck/v1", "deck": {"template": "base", "template_sha256": sha, "brand": "leo-lions", "variant": "lions", "size": "13.333x7.5in", "locale": "pt-BR", "notas": True, "modelo_catalogo": "brands/leo-lions/decks/modelos.json"}, "slides": [{"modelo": "capa_foto", "titulo": "Abertura", "subtitulo": "Encontro 2027", "notas": "nota-capa"}, {"modelo": "imagem_texto", "titulo": "Ideia", "corpo": ["um", "dois"]}, {"modelo": "secao", "titulo": "Fim"}]}
    (root / "deck.yaml").write_text(yaml.safe_dump(deck, allow_unicode=True), encoding="utf-8")
    (root / "out").mkdir(parents=True, exist_ok=True)
    return sha
def _run(root, *names):
    st = _steps(); ctx = _ctx(root)
    for n in names:
        st[n].run(ctx)
def _out(root):
    from pptx import Presentation
    path = next((root / "out").glob("*.pptx"))
    return path, Presentation(str(path))
def test_compose_origem_e_valores(tmp_path):
    import json
    _base(tmp_path); _run(tmp_path, "deck", "template", "compose")
    sl = json.loads((tmp_path / "work/deck/compose.json").read_text(encoding="utf-8"))["slides"]
    assert [s["modelo"] for s in sl] == ["capa_foto", "imagem_texto", "secao"]
    assert [s["origem"] for s in sl] == [1, 3, 2]
    assert sl[0]["valores"]["titulo"] == "Abertura" and sl[0]["valores"]["subtitulo"] == "Encontro 2027"
    assert sl[1]["valores"]["titulo"] == "Ideia" and sl[1]["valores"]["corpo"] == ["um", "dois"]
    assert sl[2]["valores"]["titulo"] == "Fim"
def test_pptx_tem_exatamente_3_slides(tmp_path):
    _base(tmp_path); _run(tmp_path, "deck", "template", "compose", "pptx")
    _, prs = _out(tmp_path)
    assert len(prs.slides) == 3
def test_pptx_textos_por_slide(tmp_path):
    _base(tmp_path); _run(tmp_path, "deck", "template", "compose", "pptx")
    _, prs = _out(tmp_path)
    by = lambda s, n: [x for x in s.shapes if x.name == n]
    assert by(prs.slides[0], "Headline")[0].text_frame.text == "Abertura"
    assert by(prs.slides[0], "Subhead")[0].text_frame.text == "Encontro 2027"
    bodies = by(prs.slides[1], "Body Copy")
    assert len(bodies) == 2
    assert any(x.text_frame.text == "Ideia" for x in bodies)
    corpo = next(x for x in bodies if x.text_frame.text != "Ideia")
    assert [p.text for p in corpo.text_frame.paragraphs] == ["um", "dois"]
    assert by(prs.slides[2], "Text Placeholder 1")[0].text_frame.text == "Fim"
def test_pptx_sem_texto_original(tmp_path):
    _base(tmp_path); _run(tmp_path, "deck", "template", "compose", "pptx")
    _, prs = _out(tmp_path)
    alltxt = "\n".join(x.text_frame.text for s in prs.slides for x in s.shapes if getattr(x, "has_text_frame", False))
    assert "Headline here" not in alltxt and "Section here" not in alltxt and "Body Copy A" not in alltxt
def test_pptx_nota_slide1(tmp_path):
    _base(tmp_path); _run(tmp_path, "deck", "template", "compose", "pptx")
    _, prs = _out(tmp_path)
    assert prs.slides[0].notes_slide.notes_text_frame.text.strip() == "nota-capa"
def test_compose_modelo_nao_suportado(tmp_path):
    import yaml
    import pytest
    from forja.errors import ForjaError
    _base(tmp_path)
    data = yaml.safe_load((tmp_path / "deck.yaml").read_text(encoding="utf-8"))
    data["slides"].append({"modelo": "grafico", "titulo": "G"})
    (tmp_path / "deck.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    _run(tmp_path, "deck", "template")
    with pytest.raises(ForjaError) as ei:
        _run(tmp_path, "compose")
    assert ei.value.code == "CONFIG_INVALID" and ei.value.details["campo"] == "modelo"
def test_compose_campo_sem_mapeamento(tmp_path):
    import yaml
    import pytest
    from forja.errors import ForjaError
    _base(tmp_path)
    data = yaml.safe_load((tmp_path / "deck.yaml").read_text(encoding="utf-8"))
    data["slides"][2]["subtitulo"] = "extra"
    (tmp_path / "deck.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    _run(tmp_path, "deck", "template")
    with pytest.raises(ForjaError) as ei:
        _run(tmp_path, "compose")
    assert ei.value.code == "CONFIG_INVALID" and ei.value.details["campo"] == "subtitulo"
def test_pptx_deterministico(tmp_path):
    _base(tmp_path); _run(tmp_path, "deck", "template", "compose", "pptx")
    _, p1 = _out(tmp_path)
    t1 = [[x.text_frame.text for x in s.shapes if getattr(x, "has_text_frame", False)] for s in p1.slides]
    _run(tmp_path, "deck", "template", "compose", "pptx")
    _, p2 = _out(tmp_path)
    t2 = [[x.text_frame.text for x in s.shapes if getattr(x, "has_text_frame", False)] for s in p2.slides]
    assert t1 == t2
