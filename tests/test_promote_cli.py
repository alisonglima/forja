"""Contrato do wrapper `scripts/od/promote_template.py` (plano:1445).

Congela: CLI `--from --brand --template --approved-by --approve-hash --check
--verify --json`; so le argv, chama `forja.templates.promote_template` e
imprime JSON, sem reimplementar copia/hash/manifesto (plano:1445, 2461).
A promocao copia para `brands/<id>/templates/<peca>.html` e grava
`manifest.json` com file/sha256/preset/design_system/approved_by/approved_at/
od_project/od_artifact (plano:1377, 1564); hash divergente e
`TEMPLATE_HASH_MISMATCH` exit 1 (plano:1564).
"""
import json, runpy, sys, types
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "od" / "promote_template.py"


def _run(monkeypatch, calls, argv, result=None, error=None):
    """Executa o script como CLI, com `forja.templates` falso e observavel."""
    import forja

    def promote(*args, **kwargs):
        calls.append((args, kwargs))
        if error is not None:
            raise error
        return result

    fake = types.ModuleType("forja.templates")
    fake.promote_template = fake.verify_template = promote
    monkeypatch.setitem(sys.modules, "forja.templates", fake)
    monkeypatch.setattr(forja, "templates", fake, raising=False)
    monkeypatch.setattr(sys, "argv", ["promote_template.py", *argv])
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    except SystemExit as exc:
        return exc.code
    return 0


def _args(tmp_path):
    src = tmp_path / "post.html"
    src.write_text("<html></html>", encoding="utf-8")
    values = {"--from": str(src), "--brand": "leo-lions", "--template": "post",
              "--approved-by": "Ana", "--approve-hash": "b" * 64}
    return [item for pair in values.items() for item in pair]


def test_promotion_forwards_every_value_and_prints_result_json(monkeypatch, capsys, tmp_path):
    out = {"schema": 1, "brand": "leo-lions", "templates": {"post": {"sha256": "b" * 64}}}
    calls = []
    code = _run(monkeypatch, calls, _args(tmp_path) + ["--json"], result=out)
    dumped = capsys.readouterr().out
    assert code == 0
    assert json.loads(dumped)["ok"] is True
    assert '"leo-lions"' in dumped and '"post"' in dumped
    assert len(calls) == 1
    args, kwargs = calls[0]
    seen = [str(value) for value in (*args, *kwargs.values())]
    for value in (str(tmp_path / "post.html"), "leo-lions", "post", "Ana", "b" * 64):
        assert value in seen


@pytest.mark.parametrize("flag", ["--check", "--verify"])
def test_check_and_verify_are_accepted_and_delegate(monkeypatch, capsys, tmp_path, flag):
    calls = []
    code = _run(monkeypatch, calls, _args(tmp_path) + [flag, "--json"], result={"ok": True})
    assert code == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    assert len(calls) == 1


@pytest.mark.parametrize("flag", ["--from", "--brand", "--template", "--approved-by", "--approve-hash"])
def test_missing_required_argument_is_usage_error(monkeypatch, capsys, tmp_path, flag):
    calls, argv = [], _args(tmp_path)
    index = argv.index(flag)
    del argv[index : index + 2]
    code = _run(monkeypatch, calls, argv + ["--json"])
    captured = capsys.readouterr()
    assert code == 2
    assert calls == []
    assert flag in captured.out + captured.err


def test_template_hash_mismatch_exits_1_and_surfaces_the_code(monkeypatch, capsys, tmp_path):
    from forja.errors import ForjaError
    # LACUNA: o contrato nao fixa o JSON/formato de erro; so o exit 1 e o codigo.
    error = ForjaError("TEMPLATE_HASH_MISMATCH", "hash diverge", details={"template": "post"})
    code = _run(monkeypatch, [], _args(tmp_path) + ["--json"], error=error)
    captured = capsys.readouterr()
    assert code == 1
    assert "TEMPLATE_HASH_MISMATCH" in captured.out + captured.err


# LACUNA: `--check`/`--verify` sem semantica no plano; so se prova aceite/delegacao.
# LACUNA/DIVERGENCIA: plano:1369 usa `--od-project`, `--od-artifact`,
# `--design-system` e `--preset`; plano:1445 nao os lista no CLI. Nao testados.
# LACUNA: a regra cita `--force` (plano:1382), mas o CLI de plano:1445 o omite.
# LACUNA: o wrapper nao le arquivo/JSON (so argv), entao nao ha entrada hostil
# propria dele; path traversal e JSON truncado sao contrato de `forja/templates.py`.
