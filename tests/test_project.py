"""Contratos de forja.project descritos no DESIGN.md."""
import pathlib

import pytest


def _step(steps, name, out_path, calls=None, source=None):
    def inputs(ctx):
        return ([source], {}) if source is not None else ([], {})

    def outputs(ctx):
        return [out_path]

    def run(ctx):
        if calls is not None:
            calls.append(name)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(name, encoding="utf-8")
        return None

    return steps.Step(
        name=name,
        doc="passo " + name,
        inputs=inputs,
        outputs=outputs,
        run=run,
        needs=[],
    )


def _ctx(steps, root, project, dry_run=False):
    return steps.Ctx(
        root=root,
        cfg=project.load_config(),
        work=project.work,
        out=project.out,
        env={},
        log=lambda message: None,
        dry_run=dry_run,
    )


def test_project_exposes_documented_paths(tmp_path):
    from forja import project

    instance = project.Project(tmp_path)
    assert (
        instance.config_path,
        instance.work,
        instance.out,
        instance.input,
    ) == (
        tmp_path / "config.yaml",
        tmp_path / "work",
        tmp_path / "out",
        tmp_path / "input",
    )


def test_project_load_config_deep_merges_defaults(tmp_path):
    from forja import config, project

    config.write_default_config(
        tmp_path / "config.yaml", voices={"provider": "mock"}
    )
    loaded = project.Project(tmp_path).load_config()
    assert loaded["voices"]["provider"] == "mock" and (
        loaded["render"]["width"] == config.DEFAULTS["render"]["width"]
    )


def test_project_load_config_rejects_invalid_config(tmp_path):
    from forja import config, project

    (tmp_path / "config.yaml").write_text("render:\n  fps: 0\n", encoding="utf-8")
    with pytest.raises(config.ConfigError):
        project.Project(tmp_path).load_config()


def test_scaffold_creates_documented_layout(tmp_path):
    from forja import project

    root = tmp_path / "meu-video"
    project.scaffold(root, "meu-video")
    assert (
        (root / "input").is_dir()
        and (root / "work").is_dir()
        and (root / "out").is_dir()
        and (root / "config.yaml").is_file()
        and (root / "cues.json").is_file()
        and (root / "lower_thirds.json").is_file()
        and (root / "AGENTS.md").is_file()
    )


def test_scaffold_returns_relative_paths(tmp_path):
    from forja import project

    root = tmp_path / "meu-video"
    created = project.scaffold(root, "meu-video")
    assert all(
        isinstance(item, str) and not pathlib.Path(item).is_absolute()
        for item in created
    ) and {
        pathlib.Path(item).name for item in created
    } >= {"config.yaml", "cues.json", "lower_thirds.json", "AGENTS.md"}


def test_scaffold_writes_empty_json_lists(tmp_path):
    from forja import project

    root = tmp_path / "meu-video"
    project.scaffold(root, "meu-video")
    assert (
        (root / "cues.json").read_text(encoding="utf-8").strip(),
        (root / "lower_thirds.json").read_text(encoding="utf-8").strip(),
    ) == ("[]", "[]")


def test_scaffold_sets_project_name_in_config(tmp_path):
    from forja import config, project

    root = tmp_path / "meu-video"
    project.scaffold(root, "meu-video")
    assert config.load_config(root / "config.yaml")["project"]["name"] == "meu-video"


def test_scaffold_writes_agents_md_for_the_workflow(tmp_path):
    from forja import project

    root = tmp_path / "meu-video"
    project.scaffold(root, "meu-video", workflow="storyboard")
    assert (root / "AGENTS.md").read_text(
        encoding="utf-8"
    ).strip() == project.agents_md("storyboard").strip()


def test_scaffold_refuses_to_overwrite_without_force(tmp_path):
    from forja import errors, project

    root = tmp_path / "meu-video"
    root.mkdir()
    (root / "config.yaml").write_text("sentinel: true\n", encoding="utf-8")
    with pytest.raises(errors.ForjaError) as excinfo:
        project.scaffold(root, "meu-video")
    assert (
        excinfo.value.code == "USAGE"
        and (root / "config.yaml").read_text(encoding="utf-8") == "sentinel: true\n"
    )


def test_scaffold_force_overwrites_existing_config(tmp_path):
    from forja import config, project

    root = tmp_path / "meu-video"
    root.mkdir()
    (root / "config.yaml").write_text("project:\n  name: antigo\n", encoding="utf-8")
    project.scaffold(root, "meu-video", force=True)
    assert config.load_config(root / "config.yaml")["project"]["name"] == "meu-video"


def test_agents_md_mentions_cycle_files_and_secret_rules():
    from forja import project

    text = project.agents_md("dub").lower()
    assert all(
        token in text
        for token in (
            "status",
            "cues.json",
            "lower_thirds.json",
            "config.yaml",
            "--json",
            "work/",
            "segredo",
            "ambiente",
        )
    )


def test_status_returns_documented_shape_for_no_steps(tmp_path):
    from forja import project

    root = tmp_path / "meu-video"
    project.scaffold(root, "meu-video")
    result = project.status(project.Project(root), [])
    assert (
        set(result) == {"project", "workflow", "steps", "next"}
        and result["project"] == "meu-video"
        and isinstance(result["workflow"], str)
        and result["steps"] == []
        and result["next"] is None
    )


def test_status_marks_steps_missing_without_a_manifest(tmp_path):
    from forja import project, steps

    root = tmp_path / "meu-video"
    project.scaffold(root, "meu-video")
    instance = project.Project(root)
    step_a = _step(steps, "clip", instance.work / "clip.mp4")
    step_b = _step(steps, "check", instance.work / "check.json")
    result = project.status(instance, [step_a, step_b])
    assert [
        (entry["name"], entry["state"], isinstance(entry["reason"], str))
        for entry in result["steps"]
    ] == [("clip", "missing", True), ("check", "missing", True)]


def test_status_next_points_to_the_first_missing_step(tmp_path):
    from forja import project, steps

    root = tmp_path / "meu-video"
    project.scaffold(root, "meu-video")
    instance = project.Project(root)
    step_a = _step(steps, "clip", instance.work / "clip.mp4")
    step_b = _step(steps, "check", instance.work / "check.json")
    result = project.status(instance, [step_a, step_b])
    assert (
        result["next"] is not None
        and "clip" in result["next"]["command"]
        and "--project" in result["next"]["command"]
        and str(root) in result["next"]["command"]
        and isinstance(result["next"]["why"], str)
        and result["next"]["why"]
    )


def test_status_marks_a_step_fresh_after_run_steps(tmp_path):
    from forja import project, steps

    root = tmp_path / "meu-video"
    project.scaffold(root, "meu-video")
    instance = project.Project(root)
    step = _step(steps, "clip", instance.work / "clip.mp4")
    steps.run_steps(_ctx(steps, root, instance), [step])
    result = project.status(instance, [step])
    assert [(entry["state"], result["next"]) for entry in result["steps"]] == [
        ("fresh", None)
    ]


def test_status_marks_a_step_stale_when_input_changes(tmp_path):
    from forja import project, steps

    root = tmp_path / "meu-video"
    project.scaffold(root, "meu-video")
    instance = project.Project(root)
    source = root / "cues.json"
    step = _step(
        steps,
        "check",
        instance.work / "check.json",
        source=source,
    )
    steps.run_steps(_ctx(steps, root, instance), [step])
    source.write_text('[{"id": "A"}]', encoding="utf-8")
    result = project.status(instance, [step])
    assert result["steps"][0]["state"] == "stale"


def test_status_next_mentions_a_stale_step(tmp_path):
    from forja import project, steps

    root = tmp_path / "meu-video"
    project.scaffold(root, "meu-video")
    instance = project.Project(root)
    source = root / "cues.json"
    step = _step(
        steps,
        "check",
        instance.work / "check.json",
        source=source,
    )
    steps.run_steps(_ctx(steps, root, instance), [step])
    source.write_text('[{"id": "B"}]', encoding="utf-8")
    result = project.status(instance, [step])
    assert (
        result["next"] is not None
        and "check" in result["next"]["command"]
        and "--project" in result["next"]["command"]
        and result["next"]["why"]
    )
