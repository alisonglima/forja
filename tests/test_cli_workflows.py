"""Contrato de CLI dos workflows novos (L-CLI-WF-01).

plano:2598: lane so em `forja/cli.py` (<=20 linhas); plano:1607 aponta os
imports de `dub`/`storyboard` (`forja/cli.py:648-649`) que faltavam.
plano:414/440 fixam 11 passos em `post` e 8 em `lote-digital`; plano:559
exige que `describe` os exponha. plano:401/404 herdam envelope e exit codes;
`get_workflow` manda nome desconhecido para `CONFIG_INVALID` exit 2.
"""
import io
import json
import pytest

POST = ("brief", "research", "copy", "template", "compose", "render", "lint", "inspect", "review", "approve", "deliver")
LOTE = ("validate-data", "template", "render-lote", "lint-lote", "sample-check", "review", "approve", "deliver")
ENVELOPE = {"ok", "data", "next_actions", "artifacts", "warnings", "cost"}

def _main(argv):
    from forja import cli
    out, err = io.StringIO(), io.StringIO()
    return cli.main(argv, env={}, out=out, err=err), json.loads(out.getvalue()), err.getvalue()

def _init(tmp_path, workflow):
    code, doc, _ = _main(["--json", "init", str(tmp_path / "p"), "--workflow", workflow])
    assert code == 0 and doc["ok"] is True
    return tmp_path / "p"

def test_describe_exposes_post_and_lote_digital_steps():
    code, doc, _ = _main(["--json", "describe"])
    assert code == 0 and set(doc) == ENVELOPE
    flows = doc["data"]["workflows"]
    assert (tuple(s["name"] for s in flows["post"]["steps"]), tuple(s["name"] for s in flows["lote-digital"]["steps"])) == (POST, LOTE)

@pytest.mark.parametrize("workflow", ["post", "lote-digital"])
def test_init_accepts_new_workflow_and_persists_it(tmp_path, workflow):
    root = _init(tmp_path, workflow)
    assert "workflow: %s" % workflow in (root / "config.yaml").read_text(encoding="utf-8")

def test_run_dry_run_uses_post_steps(tmp_path):
    root = _init(tmp_path, "post")
    code, doc, _ = _main(["--json", "--project", str(root), "run", "--only", "brief", "--dry-run"])
    assert code == 0 and set(doc) == ENVELOPE
    assert [(s["step"], s["status"]) for s in doc["data"]["steps"]] == [("brief", "would_run")]

def test_run_rejects_step_from_other_workflow(tmp_path):
    root = _init(tmp_path, "post")
    code, doc, _ = _main(["--json", "--project", str(root), "run", "--only", "validate-data", "--dry-run"])
    assert (code, doc["ok"], doc["error"]["code"]) == (2, False, "USAGE")
    assert set(doc["error"]) == {"code", "msg", "hint", "retryable", "details"}
    assert tuple(doc["error"]["details"]["steps"]) == POST

def test_unknown_workflow_in_config_fails_closed(tmp_path):
    root = _init(tmp_path, "post")
    (root / "config.yaml").write_text("project:\n  workflow: ../../post\n", encoding="utf-8")
    code, doc, err = _main(["--json", "--project", str(root), "status"])
    assert (code, doc["error"]["code"], set(doc["error"])) == (2, "CONFIG_INVALID", {"code", "msg", "hint", "retryable", "details"})
    assert "Traceback" not in err
