"""Contrato lote-digital (T-LOTE-01): congela L-LOTE-01 + 4 etapas.
Orquestrador 8 passos em ordem (plano:2552-2565); dados e limites
(plano:442-461); erros LOTE_TOO_BIG/NAME_COLLISION (plano:479-480) e
FORMAT_UNSUPPORTED (plano:472); correcoes do orquestrador (plano:2872).
Etapas: run_validate_data/run_render_lote/run_sample_check/run_deliver_lote
(plano:2573,2586-2590). Sem rede/relogio; kit/contraste injetaveis.
"""
from __future__ import annotations
import csv, json
import pytest
def _csv(p, ls):
    import csv as _c
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = _c.DictWriter(f, fieldnames=["nome", "texto", "formato"]); w.writeheader(); w.writerows(ls)
def test_orquestrador_ordena_os_8_passos():
    from forja.workflows import lote_digital as m
    s = m.steps_factory()
    assert [x.name for x in s] == ["validate-data", "template", "render-lote", "lint-lote", "sample-check", "review", "approve", "deliver"]
    assert isinstance(m.FILES, dict) and all(x.doc.strip() for x in s)
def test_validate_converte_acentos_quebra_e_slug(tmp_path):
    from forja.workflows import lote_validate as v
    src = tmp_path / "l.csv"; _csv(src, [{"nome": "João Conceição", "texto": "Ana\nPaula", "formato": "ig-portrait"}, {"nome": "Maria", "texto": "oi", "formato": "ig-portrait"}])
    out = tmp_path / "p.json"; assert v.run_validate_data(src, out, formatos=["ig-portrait"])["linhas"] == 2
    pl = json.loads(out.read_text(encoding="utf-8"))
    assert (pl[0]["slug"], pl[0]["texto"]) == ("joao-conceicao", "Ana\nPaula")
def test_validate_limite_200_linhas_e_400_arquivos(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import lote_validate as v
    src = tmp_path / "l.csv"; _csv(src, [{"nome": "n%d" % i, "texto": "t", "formato": "a"} for i in range(201)])
    with pytest.raises(ForjaError) as e: v.run_validate_data(src, tmp_path / "p.json", formatos=["a"])
    assert (e.value.code, e.value.exit_code) == ("LOTE_TOO_BIG", 2)
    _csv(src, [{"nome": "n0", "texto": "t", "formato": "f"}]); 
    with pytest.raises(ForjaError) as e2: v.run_validate_data(src, tmp_path / "q.json", formatos=["f"] * 401)
    assert e2.value.code == "LOTE_TOO_BIG"
def test_validate_colisao_de_slug_da_name_collision(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import lote_validate as v
    src = tmp_path / "l.csv"; _csv(src, [{"nome": "José Silva", "texto": "a", "formato": "a"}, {"nome": "Jose Silva", "texto": "b", "formato": "a"}])
    with pytest.raises(ForjaError) as e: v.run_validate_data(src, tmp_path / "p.json", formatos=["a"])
    assert (e.value.code, e.value.exit_code, e.value.retryable) == ("NAME_COLLISION", 2, False)
def test_validate_formato_fora_da_matriz(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import lote_validate as v
    src = tmp_path / "l.csv"; _csv(src, [{"nome": "Ana", "texto": "t", "formato": "zx"}])
    with pytest.raises(ForjaError) as e: v.run_validate_data(src, tmp_path / "p.json", formatos=["ig-portrait"])
    assert (e.value.code, e.value.exit_code) == ("FORMAT_UNSUPPORTED", 2)
def test_validate_entrada_ausente_e_vazia(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import lote_validate as v
    with pytest.raises(ForjaError) as e: v.run_validate_data(tmp_path / "nope.csv", tmp_path / "p.json")
    assert e.value.code == "MISSING_INPUT"
    src = tmp_path / "v.csv"; _csv(src, [])
    with pytest.raises(ForjaError) as e2: v.run_validate_data(src, tmp_path / "q.json")
    assert e2.value.code == "MISSING_INPUT"
def test_validate_hostil_ponto_ponto_e_json_truncado(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import lote_validate as v
    with pytest.raises(ForjaError) as e: v.run_validate_data(tmp_path / ".." / "f.csv", tmp_path / "p.json")
    assert e.value.code == "CONFIG_INVALID"
    q = tmp_path / "l.json"; q.write_text('[{"nome": "Ana", ', encoding="utf-8")
    with pytest.raises(ForjaError) as e2: v.run_validate_data(q, tmp_path / "q.json")
    assert e2.value.code == "MISSING_INPUT"
def test_render_caminho_feliz_com_kit_injetado(tmp_path):
    from forja.workflows import lote_render as r
    pl = tmp_path / "p.json"; pl.write_text(json.dumps([{"slug": "ana", "formato": "ig-portrait"}]), encoding="utf-8")
    out = tmp_path / "r"; arts = r.run_render_lote(pl, out, export=lambda s, f, d: d.write_bytes(b"P"))
    assert arts == ["ana"] and (out / "ana.png").read_bytes() == b"P"
def test_render_sem_pre_requisito_e_provedor_falha(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import lote_render as r
    pl = tmp_path / "p.json"; pl.write_text(json.dumps([{"slug": "ana", "formato": "ig-portrait"}]), encoding="utf-8")
    def sem_kit(s, f, d): raise FileNotFoundError("npx")
    with pytest.raises(ForjaError) as e: r.run_render_lote(pl, tmp_path / "a", export=sem_kit)
    assert (e.value.code, e.value.exit_code) == ("MISSING_PREREQ", 4)
    def quebra(s, f, d): raise RuntimeError("sem json")
    with pytest.raises(ForjaError) as e2: r.run_render_lote(pl, tmp_path / "b", export=quebra)
    assert (e2.value.code, e2.value.exit_code) == ("PROVIDER_ERROR", 3)
def test_sample_amostra_deterministica_e_happy(tmp_path):
    from forja.workflows import lote_sample as s
    pl = tmp_path / "p.json"; pl.write_text(json.dumps([{"slug": "ana", "nome": "Ana", "texto": "oi", "qr": "a"}, {"slug": "nome-bem-longo", "nome": "Nome Bem Longo", "texto": "l1\nl2", "qr": "bb"}]), encoding="utf-8")
    rd = tmp_path / "r"; rd.mkdir(); (rd / "ana.png").write_bytes(b"PA"); (rd / "nome-bem-longo.png").write_bytes(b"PB")
    sm = tmp_path / "s.json"; assert s.run_sample_check(pl, rd, sm, contraste=lambda x: 7.0, vistos=frozenset())["total"] == 2
    assert json.loads(sm.read_text(encoding="utf-8"))["amostra"][0] == "ana"
def test_sample_contraste_baixo_reprova(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import lote_sample as s
    pl = tmp_path / "p.json"; pl.write_text(json.dumps([{"slug": "ana", "nome": "Ana", "texto": "oi", "qr": "a"}]), encoding="utf-8")
    rd = tmp_path / "r"; rd.mkdir(); (rd / "ana.png").write_bytes(b"P")
    with pytest.raises(ForjaError) as e: s.run_sample_check(pl, rd, tmp_path / "s.json", contraste=lambda x: 2.0)
    assert (e.value.code, e.value.exit_code) == ("CONTRAST_PHOTO", 1)
def test_sample_arte_duplicada_reprova(tmp_path):
    import hashlib
    from forja.errors import ForjaError
    from forja.workflows import lote_sample as s
    pl = tmp_path / "p.json"; pl.write_text(json.dumps([{"slug": "ana", "nome": "Ana", "texto": "oi", "qr": "a"}]), encoding="utf-8")
    rd = tmp_path / "r"; rd.mkdir(); (rd / "ana.png").write_bytes(b"IGUAL")
    with pytest.raises(ForjaError) as e: s.run_sample_check(pl, rd, tmp_path / "s.json", contraste=lambda x: 7.0, vistos=frozenset([hashlib.sha256(b"IGUAL").hexdigest()]))
    assert e.value.code == "DUPLICATE_ARTIFACT"
def test_sample_qr_longo_demais_reprova(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import lote_sample as s
    pl = tmp_path / "p.json"; pl.write_text(json.dumps([{"slug": "ana", "nome": "Ana", "texto": "oi", "qr": "x" * 2001}]), encoding="utf-8")
    rd = tmp_path / "r"; rd.mkdir(); (rd / "ana.png").write_bytes(b"P")
    with pytest.raises(ForjaError) as e: s.run_sample_check(pl, rd, tmp_path / "s.json", contraste=lambda x: 7.0)
    assert e.value.code == "GATE_FAILED"
    # LACUNA: plano:442-460 fixa QR<=2000; decodificacao do QR cabe ao lint (kit check).
def test_deliver_pacote_zip_indice(tmp_path):
    import hashlib
    from forja.workflows import lote_deliver as d
    rd = tmp_path / "r"; rd.mkdir(); (rd / "ana.png").write_bytes(b"P")
    ap = tmp_path / "a.json"; h = hashlib.sha256(b"P").hexdigest()
    ap.write_text(json.dumps({"artifacts": [{"path": "ana.png", "sha256": h, "bytes": 1}], "hash": {"valor": h}}), encoding="utf-8")
    z = tmp_path / "lote.zip"; assert d.run_deliver_lote(rd, ap, z, agora="2026-11-11T00:00:00Z")["total"] == 1 and z.is_file()
def test_deliver_aprovacao_vencida_bloqueia(tmp_path):
    from forja.errors import ForjaError
    from forja.workflows import lote_deliver as d
    rd = tmp_path / "r"; rd.mkdir(); (rd / "ana.png").write_bytes(b"TROCADO")
    ap = tmp_path / "a.json"; ap.write_text(json.dumps({"artifacts": [{"path": "ana.png", "sha256": "0" * 64, "bytes": 7}], "hash": {"valor": "0" * 64}}), encoding="utf-8")
    with pytest.raises(ForjaError) as e: d.run_deliver_lote(rd, ap, tmp_path / "l.zip", agora="2026-11-11T00:00:00Z")
    assert (e.value.code, e.value.exit_code) == ("APPROVAL_STALE", 1)
    # LACUNA: ASSET_MISSING do deliver depende de forja/assets.py (L-ASSETS-01), fora deste contrato.
