"""Contratos de forja.describe descritos no DESIGN.md."""
import json

import pytest


def _step(steps, name, doc, needs=None):
    return steps.Step(
        name=name,
        doc=doc,
        inputs=lambda ctx: ([], {}),
        outputs=lambda ctx: [],
        run=lambda ctx: None,
        needs=list(needs or []),
    )


def test_describe_returns_documented_top_level_keys():
    from forja import describe

    data = describe.describe({}, "1.0.0")
    assert set(data) == {
        "version",
        "exit_codes",
        "error_codes",
        "commands",
        "workflows",
        "providers",
        "schemas",
    }


def test_describe_passes_version_through():
    from forja import describe

    assert describe.describe({}, "9.9.9")["version"] == "9.9.9"


def test_describe_exposes_every_error_code():
    from forja import describe, errors

    data = describe.describe({}, "1.0.0")
    assert set(data["error_codes"]) == set(errors.ERROR_CODES)


def test_describe_error_codes_keep_exit_and_retryable():
    from forja import describe, errors

    info = describe.describe({}, "1.0.0")["error_codes"]["MISSING_KEY"]
    assert (info["exit"], info["retryable"]) == (
        errors.ERROR_CODES["MISSING_KEY"]["exit"],
        errors.ERROR_CODES["MISSING_KEY"]["retryable"],
    )


def test_describe_exposes_exit_codes_table():
    from forja import describe

    assert describe.describe({}, "1.0.0")["exit_codes"]


def test_describe_lists_documented_commands():
    from forja import describe

    names = {command["name"] for command in describe.describe({}, "1.0.0")["commands"]}
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


def test_describe_command_entries_have_documented_shape():
    from forja import describe

    commands = describe.describe({}, "1.0.0")["commands"]
    assert commands and all(
        {"name", "summary", "args"} <= set(command)
        and isinstance(command["name"], str)
        and isinstance(command["summary"], str)
        for command in commands
    )


def test_describe_keeps_workflows_mapping_empty_when_none_given():
    from forja import describe

    assert describe.describe({}, "1.0.0")["workflows"] == {}


def test_describe_includes_workflow_steps_and_files():
    from forja import describe, steps, workflows

    files = {
        "agent_writes": ["cues.json"],
        "generated": ["work/clip.mp4"],
    }

    def factory():
        return [
            _step(steps, "clip", "Corta o clipe"),
            _step(steps, "check", "Valida as cues", ["clip"]),
        ]

    workflows.register_workflow("describe-flow", "Fluxo de teste", factory, files)
    workflow = workflows.get_workflow("describe-flow")
    data = describe.describe({"describe-flow": workflow}, "1.0.0")
    entry = data["workflows"]["describe-flow"]
    assert (
        entry["summary"] == "Fluxo de teste"
        and [
            (step["name"], step["doc"], step["needs"]) for step in entry["steps"]
        ]
        == [("clip", "Corta o clipe", []), ("check", "Valida as cues", ["clip"])]
        and entry["files"] == files
    )


def test_describe_includes_config_defaults_in_schemas():
    from forja import config, describe

    assert describe.describe({}, "1.0.0")["schemas"]["config"] == config.DEFAULTS


def test_describe_cues_schema_mentions_required_fields():
    from forja import describe

    schema = describe.describe({}, "1.0.0")["schemas"]["cues"]
    text = json.dumps(schema)
    assert all(field in text for field in ("id", "t0", "t1", "text"))


def test_describe_providers_come_from_registry():
    from forja import describe, registry

    registry.reset_for_tests()
    try:

        @registry.register("tts", "describe-provider", note="fake")
        def factory():
            return object()

        data = describe.describe({}, "1.0.0")
        assert any(
            provider["name"] == "describe-provider" for provider in data["providers"]
        )
    finally:
        registry.reset_for_tests()


def test_describe_init_matches_the_optional_source_contract():
    """Sem --source o init cria um projeto storyboard; --workflow tambem existe."""
    from forja import describe

    command = next(
        item for item in describe.describe({}, "1.0.0")["commands"] if item["name"] == "init"
    )
    args = {arg["name"]: arg for arg in command["args"]}
    assert args["dir"]["required"] is True
    assert args["--source"]["required"] is False
    assert "--workflow" in args


def test_describe_lists_builtin_voice_providers():
    from forja import describe

    names = {item["name"] for item in describe.describe({}, "1.0.0")["providers"]}
    assert {"files", "mock", "gemini"} <= names
