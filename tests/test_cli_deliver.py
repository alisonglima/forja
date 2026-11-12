"""Contrato do `forja deliver` (congela L-CLI-DELIVER-01, plano:2629).
`deliver --post --by <nome> --confirm [--json]` (§4.6.5, plano:485-509):
`--by` vazio exit 2 (plano:532); sem `--confirm` nao grava;
hash divergente `APPROVAL_STALE` exit 1 sem transicao (plano:503);
`aprovado->entregue` grava estado+evento; idempotente; envelope (plano:401,506).
# LACUNA: `hash_piece` e de L-APR-HASH-01; `hash.valor` = sha256 dos bytes (plano:510-543)."""
import hashlib
import io
import json
PECA, PACOTE = "post-dia-x", "out/post-dia-x"
ARTEFATOS = ("arte.png", "legenda.txt", "hashtags.txt", "alt.txt", "horario.json", "manifesto-ia.json")
def _run(cli, argv):
    out, err = io.StringIO(), io.StringIO()
    return cli.main(argv, env={}, out=out, err=err), out.getvalue(), err.getvalue()
def _argv(root, *extra):
    return ["--project", str(root), "--json", "deliver", "--post", *extra]
def _projeto(tmp_path, estado="aprovado", ruim=None, falta=()):
    root = tmp_path / "proj"
    (root / "work").mkdir(parents=True)
    (root / "out" / PECA).mkdir(parents=True)
    (root / "config.yaml").write_text("project:\n  name: demo\n", encoding="utf-8")
    (root / "brief.yaml").write_text("version: 1\nobjective: O\naudience: A\ntone: T\npiece: %s\nbrand_id: leo\nformat: ig-portrait\n" % PECA, encoding="utf-8")
    blob = b"arte-falsa-512"
    digest = hashlib.sha256(blob).hexdigest()
    for nome in ARTEFATOS:
        if nome not in falta:
            (root / "out" / PECA / nome).write_bytes(blob if nome == "arte.png" else b"x")
    (root / "out" / PECA / "manifest.json").write_text(json.dumps({"peca": PECA, "arquivos": list(ARTEFATOS)}), encoding="utf-8")
    base = {"schema_version": 2, "script": True, "voice": True, "overlays": True, "publish": False, "by": "Ana", "at": "2026-11-11T18:00:00Z"}
    base.update({"piece": PECA, "brand_id": "leo", "format": "ig-portrait", "brief": {"sha256": hashlib.sha256(b"brief").hexdigest(), "by": "Ana", "at": base["at"]}, "artifacts": [{"path": PACOTE + "/arte.png", "sha256": digest, "bytes": len(blob)}]})
    base["hash"] = {"algoritmo": "sha256", "valor": digest, "arquivo": PACOTE + "/arte.png", "bytes": len(blob)}
    (root / "approvals.json").write_text(json.dumps(base), encoding="utf-8")
    alvo = root / "work" / "estado.json"
    if ruim == "truncado":
        alvo.write_text('{"estado": "aprova', encoding="utf-8")
    elif ruim == "lista":
        alvo.write_text("[]", encoding="utf-8")
    elif estado is not None:
        alvo.write_text(json.dumps({"schema_version": 1, "estado": estado, "artefato": base["artifacts"][0], "aprovacao": {"by": "Ana", "at": base["at"], "sha256": digest}, "historico": []}), encoding="utf-8")
    return root, digest
def test_deliver_help_expoe_flags():
    from forja import cli
    code, out, _ = _run(cli, ["deliver", "--help"])
    assert code == 0 and "--post" in out and "--by" in out and "--confirm" in out
def test_deliver_by_vazio_e_uso_exit_2(tmp_path):
    from forja import cli
    root, _ = _projeto(tmp_path)
    code, out, _ = _run(cli, _argv(root, "--by", "", "--confirm"))
    doc = json.loads(out)
    assert (code, doc["error"]["code"]) == (2, "USAGE")
    assert "--by" in doc["error"]["msg"] + doc["error"]["hint"]
def test_deliver_sem_confirm_nao_grava(tmp_path):
    from forja import cli
    root, _ = _projeto(tmp_path)
    antes = (root / "work" / "estado.json").read_bytes()
    code, out, _ = _run(cli, _argv(root, "--by", "Ana"))
    doc = json.loads(out)
    assert (code, doc["ok"], doc["data"]["estado"]) == (0, True, "aprovado")
    assert any("--confirm" in a.get("command", "") for a in doc["next_actions"])
    assert (root / "work" / "estado.json").read_bytes() == antes and not (root / "work" / "events.ndjson").exists()
def test_deliver_hash_alterado_e_stale_sem_transicao(tmp_path):
    from forja import cli
    root, _ = _projeto(tmp_path)
    (root / "out" / PECA / "arte.png").write_bytes(b"arte-adulterada!")
    code, out, _ = _run(cli, _argv(root, "--by", "Ana", "--confirm"))
    doc = json.loads(out)
    estado = json.loads((root / "work" / "estado.json").read_text(encoding="utf-8"))
    assert (code, doc["ok"], doc["error"]["code"]) == (1, False, "APPROVAL_STALE")
    assert set(doc["error"]) == {"code", "msg", "hint", "retryable", "details"}
    assert {"expected", "current", "piece", "path"} <= set(doc["error"]["details"] or {}) and estado["estado"] == "aprovado"
def test_deliver_aprovado_para_entregue_grava_estado_e_evento(tmp_path):
    from forja import cli
    root, digest = _projeto(tmp_path)
    code, out, _ = _run(cli, _argv(root, "--by", "Ana", "--confirm"))
    doc = json.loads(out)
    assert (code, doc["ok"], doc["cost"]) == (0, True, None) and set(doc) == {"ok", "data", "next_actions", "artifacts", "warnings", "cost"}
    dados = doc["data"]
    assert (dados["estado"], dados["de"], dados["para"], dados["pacote"]) == ("entregue", "aprovado", "entregue", PACOTE)
    assert (dados["aprovacao"]["by"], dados["aprovacao"]["sha256"]) == ("Ana", digest)
    estado = json.loads((root / "work" / "estado.json").read_text(encoding="utf-8"))
    ultimo = estado["historico"][-1]
    assert estado["estado"] == "entregue" and (ultimo["de"], ultimo["para"], ultimo["por"], ultimo["sha256"]) == ("aprovado", "entregue", "Ana", digest) and ultimo["em"].endswith("Z")
    evento = json.loads((root / "work" / "events.ndjson").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert (evento["step"], evento["status"], evento["by"], evento["de"], evento["para"]) == ("deliver", "ok", "Ana", "aprovado", "entregue")
def test_deliver_entregue_e_idempotente(tmp_path):
    from forja import cli
    root, _ = _projeto(tmp_path)
    argv = _argv(root, "--by", "Ana", "--confirm")
    code1, _, _ = _run(cli, argv)
    code2, out2, _ = _run(cli, argv)
    linhas = (root / "work" / "events.ndjson").read_text(encoding="utf-8").strip().splitlines()
    estado = json.loads((root / "work" / "estado.json").read_text(encoding="utf-8"))
    assert (code1, code2) == (0, 0) and json.loads(out2)["data"]["estado"] == "entregue" and len(linhas) == 1 and len(estado["historico"]) == 1
def test_deliver_sem_aprovacao_e_gate_failed(tmp_path):
    from forja import cli
    root, _ = _projeto(tmp_path / "a", estado=None)
    code, out, _ = _run(cli, _argv(root, "--by", "Ana", "--confirm"))
    assert (code, json.loads(out)["error"]["code"]) == (1, "GATE_FAILED")
    root, _ = _projeto(tmp_path / "b", estado="render_pendente")
    code, out, _ = _run(cli, _argv(root, "--by", "Ana", "--confirm"))
    assert (code, json.loads(out)["error"]["code"]) == (1, "GATE_FAILED")
def test_deliver_estado_invalido_falha_fechado(tmp_path):
    from forja import cli
    for ruim in ("truncado", "lista"):
        root, _ = _projeto(tmp_path / ruim, ruim=ruim)
        code, out, err = _run(cli, _argv(root, "--by", "Ana", "--confirm"))
        assert (code, json.loads(out)["error"]["code"]) == (1, "GATE_FAILED")
        assert "Traceback" not in out and "Traceback" not in err
def test_deliver_pacote_falho_e_asset_missing(tmp_path):
    from forja import cli
    root, _ = _projeto(tmp_path / "a", falta=("legenda.txt",))
    code, out, _ = _run(cli, _argv(root, "--by", "Ana", "--confirm"))
    assert (code, json.loads(out)["error"]["code"]) == (2, "ASSET_MISSING")
    root, _ = _projeto(tmp_path / "b")
    (root / "out" / PECA / "manifest.json").unlink()
    code, out, _ = _run(cli, _argv(root, "--by", "Ana", "--confirm"))
    assert (code, json.loads(out)["error"]["code"]) == (2, "ASSET_MISSING")
def test_deliver_sem_rede_nem_agendamento():
    from forja import cli
    from pathlib import Path
    fonte = Path(cli.__file__).read_text(encoding="utf-8")
    assert "socket" not in fonte and "requests" not in fonte and "urllib" not in fonte and "graph.facebook" not in fonte
