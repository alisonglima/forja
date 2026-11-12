"""Contrato CLI de aprovacao post/lote-digital (T-CLI-APR-01).
Congela `forja approve --post --hash <arquivo> --brief --by <nome>`:
- plano:2645: `--post` sem `--by` -> exit 2; `--hash` que nao confere ->
  `APPROVAL_STALE` exit 1 sem gravar; `--brief` regrava o bloco do brief.
- plano:526: v2 preserva `schema_version/piece/brand_id/format/brief/artifacts/hash`.
- plano:710: `brief.sha256` do YAML normalizado; `hash.valor` cobre brief +
  `artifacts[]`; mesma entrada => mesmo hash; comentario/ordem nao invalidam.
- plano:465: 0 ok, 1 stale/gate, 2 uso/pacote; `retryable=false` nos novos.
- plano:401: envelope ok (`cost:null`); falha sem traceback via `error_payload`.
"""
import hashlib
import io
import json

BRIEF_OK = (
    "version: 1\nobjective: Anunciar o dia X\n"
    "audience: Seguidores do clube\ntone: Direto\n"
    "duration_s: 15\nmust_include: []\nmust_avoid: []\n"
    "piece: post-dia-x\nbrand_id: leo-lions\nformat: ig-portrait\n"
)


def _run(cli, argv):
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(argv, env={}, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def _run_json(cli, argv):
    code, out, err = _run(cli, argv)
    return code, json.loads(out), err


def _write_project(tmp_path, brief=BRIEF_OK):
    root = tmp_path / "proj"
    (root / "out").mkdir(parents=True)
    (root / "config.yaml").write_text("project:\n  name: proj\n", encoding="utf-8")
    (root / "brief.yaml").write_text(brief, encoding="utf-8")
    return root


def _write_piece(root, data=b"conteudo-da-peca-1"):
    target = root / "out" / "feed.png"
    target.write_bytes(data)
    return target


def test_approve_post_hash_happy_path(tmp_path):
    from forja import cli

    data = b"conteudo-da-peca-1"
    root = _write_project(tmp_path)
    target = _write_piece(root, data)
    want = hashlib.sha256(data).hexdigest()
    code, doc, err = _run_json(cli, ["--json", "--project", str(root), "approve", "--post", "--hash", str(target), "--brief", "--by", "Ana"])
    assert code == 0 and doc["ok"] is True and doc["cost"] is None
    assert doc["data"]["hash"]["valor"] == want and doc["data"]["hash"]["bytes"] == len(data)
    assert doc["data"]["hash"]["algoritmo"] == "sha256" and doc["data"]["hash"]["arquivo"] == "out/feed.png"
    saved = json.loads((root / "approvals.json").read_text(encoding="utf-8"))
    assert saved["hash"]["valor"] == want and saved["artifacts"] == [{"path": "out/feed.png", "sha256": want, "bytes": len(data)}]
    assert (saved["piece"], saved["brand_id"], saved["format"]) == ("post-dia-x", "leo-lions", "ig-portrait")
    assert doc["data"]["brief"]["sha256"] == saved["brief"]["sha256"] and "traceback" not in err.lower()


def test_approve_post_hash_mismatch_is_stale(tmp_path):
    from forja import cli

    root = _write_project(tmp_path)
    target = _write_piece(root, b"original-1")
    argv = ["--json", "--project", str(root), "approve", "--post", "--hash", str(target), "--by", "Ana"]
    code, _, _ = _run_json(cli, argv)
    assert code == 0
    before = (root / "approvals.json").read_text(encoding="utf-8")
    target.write_bytes(b"adulterado-depois")
    code, doc, err = _run_json(cli, argv)
    assert code == 1 and doc["ok"] is False and doc["error"]["code"] == "APPROVAL_STALE"
    assert doc["error"]["retryable"] is False and {"expected", "current", "piece", "path"} <= set(doc["error"]["details"])
    assert (root / "approvals.json").read_text(encoding="utf-8") == before and "traceback" not in err.lower()


def test_approve_brief_rewrites_block(tmp_path):
    from forja import cli

    root = _write_project(tmp_path)
    argv = ["--json", "--project", str(root), "approve", "--brief", "--by", "Ana"]
    code, doc, _ = _run_json(cli, argv)
    assert code == 0 and doc["ok"] is True
    first = json.loads((root / "approvals.json").read_text(encoding="utf-8"))["brief"]
    assert first["by"] == "Ana" and len(bytes.fromhex(first["sha256"])) == 32
    assert doc["data"]["brief"]["sha256"] == first["sha256"]
    (root / "brief.yaml").write_text(BRIEF_OK.replace("tone: Direto\n", "") + "tone: Direto\n# so comentario\n", encoding="utf-8")
    code, doc, _ = _run_json(cli, argv)
    assert code == 0 and doc["data"]["brief"]["sha256"] == first["sha256"]


def test_approve_brief_incomplete_is_error(tmp_path):
    from forja import cli

    root = _write_project(tmp_path, BRIEF_OK.replace("objective: Anunciar o dia X", "objective: ''"))
    code, doc, _ = _run_json(cli, ["--json", "--project", str(root), "approve", "--brief", "--by", "Ana"])
    assert code == 2 and doc["ok"] is False and doc["error"]["code"] == "BRIEF_INCOMPLETE"
    assert doc["error"]["retryable"] is False
    # LACUNA: contrato nao nomeia o codigo p/ brief.yaml ausente; nao verificado.


def test_approve_by_required_for_post(tmp_path):
    from forja import cli

    root = _write_project(tmp_path)
    target = _write_piece(root)
    base = ["--json", "--project", str(root), "approve", "--post", "--hash", str(target)]
    code, doc, _ = _run_json(cli, base)
    assert code == 2 and doc["ok"] is False and doc["error"]["code"] == "USAGE"
    code, doc, _ = _run_json(cli, [*base, "--by", ""])
    assert code == 2 and doc["error"]["code"] == "USAGE"
    code, doc, _ = _run_json(cli, [*base, "--by", "Ana"])
    assert code == 0 and doc["ok"] is True


def test_approve_post_hash_hostile_path(tmp_path):
    from forja import cli

    root = _write_project(tmp_path)
    outside = tmp_path / "fora.png"
    outside.write_bytes(b"fora-do-projeto")
    evil = str(root / ".." / "fora.png")
    code, doc, _ = _run_json(cli, ["--json", "--project", str(root), "approve", "--post", "--hash", evil, "--by", "Ana"])
    assert code == 2 and doc["ok"] is False
    assert not (root / "approvals.json").exists() and outside.read_bytes() == b"fora-do-projeto"
    # LACUNA: contrato nao nomeia o codigo p/ fuga com `..`; so o exit 2 (plano:506).
    # LACUNA: `--hash <hex>` (plano:710) x `--hash <arquivo>` (plano:518/2645); vale arquivo.
