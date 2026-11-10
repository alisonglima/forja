"""Contratos de forja.cli (v2) descritos no DESIGN.md."""
import io
import json
from types import SimpleNamespace

import pytest


def _run(cli, argv, env=None):
    out = io.StringIO()
    err = io.StringIO()
    code = cli.main(argv, env={} if env is None else env, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def _run_json(cli, argv, env=None):
    code, out, err = _run(cli, argv, env=env)
    return code, json.loads(out), err


def _write_project(tmp_path, name="meu-video"):
    root = tmp_path / name
    (root / "input").mkdir(parents=True)
    (root / "work").mkdir()
    (root / "out").mkdir()
    (root / "config.yaml").write_text(
        "project:\n  name: {}\n".format(name), encoding="utf-8"
    )
    (root / "cues.json").write_text("[]", encoding="utf-8")
    (root / "lower_thirds.json").write_text("[]", encoding="utf-8")
    return root


def _fake_source(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"not-a-real-video")
    return source


def _init(cli, tmp_path, extra=()):
    return _run_json(
        cli,
        [
            "--json",
            "init",
            str(tmp_path / "proj"),
            "--source",
            str(_fake_source(tmp_path)),
            *extra,
        ],
    )


def test_describe_json_exits_zero():
    from forja import cli

    code, _, _ = _run_json(cli, ["--json", "describe"], env={})
    assert code == 0


def test_describe_json_has_documented_top_level_keys():
    from forja import cli

    _, doc, _ = _run_json(cli, ["--json", "describe"], env={})
    assert set(doc) == {
        "version",
        "exit_codes",
        "error_codes",
        "commands",
        "workflows",
        "providers",
        "schemas",
    }


def test_describe_lists_the_documented_commands():
    from forja import cli

    _, doc, _ = _run_json(cli, ["--json", "describe"], env={})
    names = {command["name"] for command in doc["commands"]}
    assert {
        "init",
        "describe",
        "status",
        "doctor",
        "run",
        "transcribe",
        "frames",
        "check",
        "voices",
        "schedule",
        "mix",
        "render",
        "qa",
        "providers",
    } <= names


def test_describe_exposes_config_defaults_as_schema():
    from forja import cli, config

    _, doc, _ = _run_json(cli, ["--json", "describe"], env={})
    assert doc["schemas"]["config"] == config.DEFAULTS


def test_describe_exposes_the_documented_error_codes():
    from forja import cli

    _, doc, _ = _run_json(cli, ["--json", "describe"], env={})
    assert {
        "CONFIG_INVALID",
        "USAGE",
        "GATE_FAILED",
        "PROVIDER_ERROR",
        "RATE_LIMITED",
        "NETWORK",
        "MISSING_PREREQ",
        "MISSING_KEY",
        "MISSING_INPUT",
        "INTERNAL",
    } <= set(doc["error_codes"])


def test_describe_registers_dub_and_storyboard_workflows():
    from forja import cli

    _, doc, _ = _run_json(cli, ["--json", "describe"], env={})
    assert {"dub", "storyboard"} <= set(doc["workflows"])


def test_describe_providers_is_a_list():
    from forja import cli

    _, doc, _ = _run_json(cli, ["--json", "describe"], env={})
    assert isinstance(doc["providers"], list)


def test_status_json_reports_the_documented_keys(tmp_path):
    from forja import cli

    root = _write_project(tmp_path)
    code, doc, _ = _run_json(
        cli, ["--json", "--project", str(root), "status"], env={}
    )
    assert code == 0 and {"project", "workflow", "steps", "next"} <= set(doc)


def test_status_reports_the_project_name(tmp_path):
    from forja import cli

    root = _write_project(tmp_path, name="meu-video")
    _, doc, _ = _run_json(
        cli, ["--json", "--project", str(root), "status"], env={}
    )
    assert doc["project"] == "meu-video"


def test_status_steps_use_the_documented_states(tmp_path):
    from forja import cli

    root = _write_project(tmp_path)
    _, doc, _ = _run_json(
        cli, ["--json", "--project", str(root), "status"], env={}
    )
    assert doc["steps"] and all(
        {"name", "state", "reason"} <= set(step)
        and step["state"] in {"fresh", "stale", "missing"}
        for step in doc["steps"]
    )


def test_status_next_points_to_a_forja_command(tmp_path):
    from forja import cli

    root = _write_project(tmp_path)
    _, doc, _ = _run_json(
        cli, ["--json", "--project", str(root), "status"], env={}
    )
    assert isinstance(doc["next"], dict) and doc["next"]["command"].startswith(
        "forja"
    ) and doc["next"]["why"]


def test_status_on_missing_project_exits_two_with_json_error(tmp_path):
    from forja import cli

    code, doc, _ = _run_json(
        cli,
        ["--json", "--project", str(tmp_path / "nao-existe"), "status"],
        env={},
    )
    assert code == 2 and doc["ok"] is False


def test_init_creates_the_documented_project_files(tmp_path):
    from forja import cli

    code, _, _ = _init(cli, tmp_path)
    root = tmp_path / "proj"
    expected = [
        "config.yaml",
        "cues.json",
        "lower_thirds.json",
        "AGENTS.md",
        "input",
        "work",
        "out",
    ]
    assert code == 0 and all((root / name).exists() for name in expected)


def test_init_writes_empty_cues_and_lower_thirds(tmp_path):
    from forja import cli

    _init(cli, tmp_path)
    root = tmp_path / "proj"
    assert [
        json.loads((root / "cues.json").read_text(encoding="utf-8")),
        json.loads((root / "lower_thirds.json").read_text(encoding="utf-8")),
    ] == [[], []]


def test_init_refuses_to_overwrite_without_force(tmp_path):
    from forja import cli

    _init(cli, tmp_path)
    code, doc, _ = _init(cli, tmp_path)
    assert code == 2 and doc["error"]["code"] == "USAGE"


def test_init_force_replaces_an_existing_project(tmp_path):
    from forja import cli

    _init(cli, tmp_path)
    code, _, _ = _init(cli, tmp_path, extra=("--force",))
    assert code == 0


def test_init_without_a_directory_is_a_usage_error():
    from forja import cli

    code, doc, _ = _run_json(cli, ["--json", "init"], env={})
    assert code == 2 and doc["error"]["code"] == "USAGE"


def test_unknown_command_exits_two():
    from forja import cli

    code, _, _ = _run(cli, ["comando-que-nao-existe"], env={})
    assert code == 2


def test_unknown_command_json_error_has_the_documented_shape():
    from forja import cli

    code, doc, _ = _run_json(
        cli, ["--json", "comando-que-nao-existe"], env={}
    )
    error = doc["error"]
    assert (
        code == 2
        and doc["ok"] is False
        and error["code"] == "USAGE"
        and {"code", "msg", "hint", "retryable"} <= set(error)
        and isinstance(error["retryable"], bool)
    )


def test_unknown_command_text_error_is_one_line_without_traceback():
    from forja import cli

    code, _, err = _run(cli, ["comando-que-nao-existe"], env={})
    assert code == 2 and len(err.strip().splitlines()) == 1 and (
        "Traceback" not in err
    )


def test_unknown_flag_is_a_usage_error():
    from forja import cli

    code, doc, _ = _run_json(
        cli, ["--json", "--flag-inexistente", "describe"], env={}
    )
    assert code == 2 and doc["error"]["code"] == "USAGE"


def test_doctor_with_empty_path_exits_four():
    from forja import cli

    code, _, _ = _run_json(cli, ["--json", "doctor"], env={"PATH": ""})
    assert code == 4


def test_doctor_with_empty_path_reports_not_ok():
    from forja import cli

    _, doc, _ = _run_json(cli, ["--json", "doctor"], env={"PATH": ""})
    assert doc["ok"] is False


def test_doctor_never_leaks_the_tts_key_value():
    from forja import cli

    secret = "segredo-super-secreto-123"
    _, out, err = _run(
        cli,
        ["--json", "doctor"],
        env={"PATH": "", "GEMINI_API_KEY": secret},
    )
    assert secret not in out and secret not in err


def test_gate_qa_fails_closed_when_qa_json_is_corrupt(tmp_path):
    from forja import cli, errors

    out = tmp_path / "out"
    out.mkdir()
    (out / "qa.json").write_text("{nao e json", encoding="utf-8")
    project = SimpleNamespace(out=out, work=tmp_path / "work")
    with pytest.raises(errors.ForjaError) as excinfo:
        cli._gate_qa(project, [], strict=True)
    assert excinfo.value.code == "GATE_FAILED"


def test_gate_check_fails_closed_when_check_json_is_corrupt(tmp_path):
    from forja import cli, errors

    work = tmp_path / "work"
    work.mkdir()
    (work / "check.json").write_text("{nao e json", encoding="utf-8")
    project = SimpleNamespace(out=tmp_path / "out", work=work)
    with pytest.raises(errors.ForjaError) as excinfo:
        cli._gate_check(project, [], strict=True)
    assert excinfo.value.code == "GATE_FAILED"
