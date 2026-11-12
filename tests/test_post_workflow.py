"""Contrato do workflow post (T-POST-01).
Congela 11 passos brief..deliver (plano:2619; plano:1452).
Orquestrador steps_factory/FILES (plano:2577; plano:1452).
Modulos run_brief/run_research/run_copy (plano:2578-2579; plano:420).
Compose run_template/run_compose + hash (plano:2580; plano:1387).
Kit run_render/run_lint com run= (plano:2581; plano:1399).
Inspect/deliver e erros novos (plano:2582-2583; plano:472).
"""
import json
import pytest

def _ctx(t, c=None):
    from forja import steps
    (t / "work").mkdir(exist_ok=True);(t / "out").mkdir(exist_ok=True)
    return steps.Ctx(root=t, cfg=c or {}, work=t / "work", out=t / "out", env={}, log=lambda m: None, dry_run=False)

def _w(p, o):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(o if isinstance(o, str) else json.dumps(o), encoding="utf-8")

def test_orquestrador_steps_factory_ordem_e_onze_passos(tmp_path):
    from forja.workflows import post
    n = [s.name for s in post.steps_factory()]
    assert n == ["brief", "research", "copy", "template", "compose", "render", "lint", "inspect", "review", "approve", "deliver"]
    assert all(hasattr(s, "inputs") and hasattr(s, "outputs") and hasattr(s, "run") for s in post.steps_factory())
    assert not {"design_system", "author", "critique", "approve_template"} & set(n)
    assert {"agent_writes", "generated"} <= set(post.FILES)

def test_brief_run_brief_feliz_escreve_brief_json(tmp_path):
    from forja.workflows import post_brief
    _w(tmp_path / "brief.yaml", "version: 1\nobjective: Lancar colecao\naudience: Jovens\ntone: Direto\n")
    assert post_brief.run_brief(_ctx(tmp_path))["ok"] is True
    assert json.loads((tmp_path / "work" / "brief.json").read_text(encoding="utf-8"))["objective"] == "Lancar colecao"

def test_brief_run_brief_incompleto_falha(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import post_brief
    _w(tmp_path / "brief.yaml", "version: 1\nobjective: ''\naudience: 'X'\ntone: 'Y'\n")
    with pytest.raises(ForjaError) as e: post_brief.run_brief(_ctx(tmp_path))
    assert (e.value.code, e.value.exit_code, e.value.retryable) == ("BRIEF_INCOMPLETE", 2, False)

def test_brief_run_brief_ausente_falha_config(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import post_brief
    with pytest.raises(ForjaError) as e: post_brief.run_brief(_ctx(tmp_path))
    assert e.value.code in ("MISSING_INPUT", "CONFIG_INVALID") and e.value.exit_code == 2

def test_content_run_research_sem_fonte_falha(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import post_content
    _w(tmp_path / "work" / "brief.json", {"objective": "X", "audience": "Y", "tone": "Z"})
    with pytest.raises(ForjaError) as e: post_content.run_research(_ctx(tmp_path))
    assert e.value.code in ("MISSING_INPUT", "BRIEF_INCOMPLETE")

def test_content_run_copy_feliz_mede_limites(tmp_path):
    from forja.workflows import post_content
    _w(tmp_path / "work" / "brief.json", {"objective": "X", "audience": "Y", "tone": "Z"})
    _w(tmp_path / "work" / "research.json", {"fontes": [{"url": "https://exemplo.test/a", "titulo": "T", "data": "2026-01-01", "trecho": "x"}]})
    assert post_content.run_copy(_ctx(tmp_path))["ok"] is True
    assert json.loads((tmp_path / "work" / "copy.json").read_text(encoding="utf-8"))["cta"]

def test_compose_run_template_hash_divergente_falha(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import post_compose
    _w(tmp_path / "brands" / "leo-lions" / "templates" / "post.html", "<div data-od-card>oi</div>")
    _w(tmp_path / "brands" / "leo-lions" / "templates" / "manifest.json", {"templates": {"post": {"file": "post.html", "sha256": "0" * 64}}})
    with pytest.raises(ForjaError) as e: post_compose.run_template(_ctx(tmp_path, {"brand_id": "leo-lions", "piece": "post"}))
    assert (e.value.code, e.value.exit_code, e.value.retryable) == ("TEMPLATE_HASH_MISMATCH", 1, False)
    assert {"brand", "template", "expected", "actual"} <= set(e.value.details)

def test_compose_run_compose_formato_fora_da_matriz_falha(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import post_compose
    _w(tmp_path / "work" / "copy.json", {"titulo": "T", "corpo": "C", "cta": "Compre", "legenda": "L", "hashtags": ["#a"], "alt": "A"})
    _w(tmp_path / "work" / "assets.json", {"assets": []})
    with pytest.raises(ForjaError) as e: post_compose.run_compose(_ctx(tmp_path, {"brand_id": "leo-lions", "piece": "post", "format": "banner-inexistente"}))
    assert (e.value.code, e.value.exit_code, e.value.retryable) == ("FORMAT_UNSUPPORTED", 2, False)

def test_compose_run_compose_asset_ausente_e_traversal_falha(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import post_compose
    _w(tmp_path / "work" / "copy.json", {"titulo": "T", "corpo": "C", "cta": "C", "legenda": "L", "hashtags": ["#a"], "alt": "A", "imagem": "../fora.png"})
    _w(tmp_path / "work" / "assets.json", {"assets": []})
    with pytest.raises(ForjaError) as e: post_compose.run_compose(_ctx(tmp_path, {"brand_id": "leo-lions", "piece": "post", "format": "ig-portrait"}))
    assert (e.value.code, e.value.exit_code) == ("ASSET_MISSING", 2)
    # LACUNA: contrato nao fixa mensagem do traversal, so o codigo.

def test_kit_run_render_feliz_usa_run_injetavel(tmp_path):
    from forja.workflows import post_kit
    _w(tmp_path / "work" / "compose" / "post.html", "<div data-od-card>t</div>")
    def fake(cmd, **k):
        p = tmp_path / "work" / "render" / "post.png";p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(b"X")
        from subprocess import CompletedProcess as C;return C(cmd, 0, "", "")
    assert post_kit.run_render(_ctx(tmp_path, {"brand_id": "leo-lions", "piece": "post", "format": "ig-portrait"}), run=fake)["ok"] is True
    assert (tmp_path / "work" / "render" / "post.png").is_file()

def test_kit_run_lint_gate_reprovado_falha(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import post_kit
    _w(tmp_path / "work" / "compose" / "post.html", "<div>sem card</div>")
    with pytest.raises(ForjaError) as e: post_kit.run_lint(_ctx(tmp_path, {"brand_id": "leo-lions", "piece": "post"}), run=lambda *a, **k: None)
    assert (e.value.code, e.value.exit_code) == ("GATE_FAILED", 1)

def test_inspect_run_inspect_contraste_e_dedup_falham(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import post_inspect
    (tmp_path / "work" / "render").mkdir(parents=True, exist_ok=True)
    (tmp_path / "work" / "render" / "post.png").write_bytes(b"X")
    _w(tmp_path / "work" / "lint" / "post.json", {"ok": True, "errors": 0, "warnings": 0})
    with pytest.raises(ForjaError) as e: post_inspect.run_inspect(_ctx(tmp_path, {"brand_id": "leo-lions", "piece": "post"}))
    assert e.value.code in ("CONTRAST_PHOTO", "DUPLICATE_ARTIFACT", "GATE_FAILED") and e.value.exit_code == 1

def test_deliver_run_deliver_stale_falha(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import post_deliver
    (tmp_path / "out" / "post").mkdir(parents=True, exist_ok=True)
    (tmp_path / "out" / "post" / "feed.png").write_bytes(b"novo")
    _w(tmp_path / "approvals.json", {"hash": {"valor": "0" * 64, "arquivo": "out/post/feed.png"}})
    with pytest.raises(ForjaError) as e: post_deliver.run_deliver(_ctx(tmp_path, {"brand_id": "leo-lions", "piece": "post"}))
    assert (e.value.code, e.value.exit_code, e.value.retryable) == ("APPROVAL_STALE", 1, False)

def test_deliver_run_deliver_pacote_incompleto_falha(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import post_deliver
    _w(tmp_path / "approvals.json", {"hash": {"valor": "abc", "arquivo": "out/post/feed.png"}})
    with pytest.raises(ForjaError) as e: post_deliver.run_deliver(_ctx(tmp_path, {"brand_id": "leo-lions", "piece": "post"}))
    assert (e.value.code, e.value.exit_code) == ("ASSET_MISSING", 2)
    # LACUNA: horario.txt (plano:428) x horario.json (plano:503); nao afirmo o nome.
