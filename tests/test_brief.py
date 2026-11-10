"""Contratos do brief humano e das aprovacoes."""
import json

import pytest


def _write_brief(root, text):
    (root / "brief.yaml").write_text(text, encoding="utf-8")


def test_missing_brief_is_a_warning(tmp_path):
    from forja import brief

    issues = brief.brief_issues(tmp_path)
    assert issues and issues[0]["code"] == "BRIEF_MISSING"
    assert issues[0]["level"] == "warn"


def test_incomplete_brief_reports_each_empty_requirement(tmp_path):
    from forja import brief

    _write_brief(tmp_path, "version: 1\nobjective: ''\naudience: ''\ntone: ''\nconsent: false\n")
    codes = [issue["code"] for issue in brief.brief_issues(tmp_path)]
    assert codes.count("BRIEF_INCOMPLETE") == 3


def test_complete_brief_has_no_issues(tmp_path):
    from forja import brief

    _write_brief(
        tmp_path,
        "version: 1\nobjective: Explicar o pedido\naudience: Time interno\ntone: Direto\nconsent: true\n",
    )
    assert brief.brief_issues(tmp_path) == []


def test_approvals_are_written_atomically_and_merge(tmp_path):
    from forja import brief

    data = brief.write_approvals(tmp_path, {"script": True}, by="Ana")
    assert data["script"] is True and data["voice"] is False
    assert data["by"] == "Ana" and data["at"].endswith("Z")
    data = brief.write_approvals(tmp_path, {"voice": True}, by="Ana")
    assert data["script"] is True and data["voice"] is True


def test_corrupt_approvals_fail_closed(tmp_path):
    from forja import brief
    from forja.errors import ForjaError

    (tmp_path / "approvals.json").write_text("{quebrado", encoding="utf-8")
    with pytest.raises(ForjaError) as excinfo:
        brief.load_approvals(tmp_path)
    assert excinfo.value.code == "GATE_FAILED"


def test_require_approvals_blocks_when_enabled(tmp_path):
    from forja import brief
    from forja.errors import ForjaError

    cfg = {"project": {"require_approvals": True}}
    with pytest.raises(ForjaError) as excinfo:
        brief.require_approvals(tmp_path, cfg, ("script", "voice"))
    assert excinfo.value.code == "GATE_FAILED"
    brief.write_approvals(tmp_path, {"script": True, "voice": True}, by="Ana")
    brief.require_approvals(tmp_path, cfg, ("script", "voice"))


def test_require_approvals_is_opt_in(tmp_path):
    from forja import brief

    brief.require_approvals(tmp_path, {"project": {"require_approvals": False}})
