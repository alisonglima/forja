"""Contratos de forja.workflows descritos no DESIGN.md."""
import pytest


class _FakeEntryPoint:
    def __init__(self, group, name, callback):
        self.group = group
        self.name = name
        self._callback = callback

    def load(self):
        return self._callback


class _FakeEntryPoints(list):
    def select(self, **kwargs):
        group = kwargs.get("group")
        return _FakeEntryPoints(
            entry for entry in self if group is None or entry.group == group
        )

    def get(self, group, default=None):
        selected = _FakeEntryPoints(
            entry for entry in self if entry.group == group
        )
        return selected or (default if default is not None else _FakeEntryPoints())


def _fake_entry_points(entries):
    def fake(*args, **kwargs):
        group = kwargs.get("group")
        if group is None and args:
            group = args[0]
        points = _FakeEntryPoints(entries)
        if group is None:
            return points
        return points.select(group=group)

    return fake


def _step(steps, name, doc, needs=None):
    return steps.Step(
        name=name,
        doc=doc,
        inputs=lambda ctx: ([], {}),
        outputs=lambda ctx: [],
        run=lambda ctx: None,
        needs=list(needs or []),
    )


def test_workflows_module_exposes_documented_api():
    from forja import workflows

    assert (
        isinstance(workflows.WORKFLOWS, dict)
        and callable(workflows.register_workflow)
        and callable(workflows.get_workflow)
        and callable(workflows.load_entry_points)
    )


def test_register_workflow_adds_named_workflow():
    from forja import workflows

    workflows.register_workflow(
        "wf-register", "Resumo", lambda: [], {"agent_writes": [], "generated": []}
    )
    assert "wf-register" in workflows.WORKFLOWS


def test_get_workflow_returns_registered_summary():
    from forja import workflows

    workflows.register_workflow(
        "wf-summary", "Resumo do fluxo", lambda: [], {"agent_writes": [], "generated": []}
    )
    assert workflows.get_workflow("wf-summary").summary == "Resumo do fluxo"


def test_get_workflow_preserves_files_mapping():
    from forja import workflows

    files = {
        "agent_writes": ["cues.json"],
        "generated": ["work/clip.mp4"],
    }
    workflows.register_workflow("wf-files", "Resumo", lambda: [], files)
    assert workflows.get_workflow("wf-files").files == files


def test_get_workflow_preserves_steps_factory():
    from forja import steps, workflows

    def factory():
        return [
            _step(steps, "clip", "Corta o clipe"),
            _step(steps, "check", "Valida as cues", ["clip"]),
        ]

    workflows.register_workflow(
        "wf-steps", "Resumo", factory, {"agent_writes": [], "generated": []}
    )
    workflow = workflows.get_workflow("wf-steps")
    assert callable(workflow.steps_factory) and [
        (step.name, step.doc, step.needs) for step in workflow.steps_factory()
    ] == [("clip", "Corta o clipe", []), ("check", "Valida as cues", ["clip"])]


def test_get_workflow_unknown_name_raises_config_invalid():
    from forja import errors, workflows

    with pytest.raises(errors.ForjaError) as excinfo:
        workflows.get_workflow("wf-nao-existe")
    assert excinfo.value.code == "CONFIG_INVALID"


def test_load_entry_points_queries_metadata(monkeypatch):
    from importlib import metadata

    from forja import workflows

    calls = []

    def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return _FakeEntryPoints()

    monkeypatch.setattr(metadata, "entry_points", fake)
    monkeypatch.setattr(workflows, "entry_points", fake, raising=False)
    workflows.load_entry_points("forja.workflows")
    assert calls


def test_load_entry_points_ignores_other_groups(monkeypatch):
    from importlib import metadata

    from forja import workflows

    def callback():
        workflows.register_workflow(
            "wf-other", "Outro", lambda: [], {"agent_writes": [], "generated": []}
        )

    entry = _FakeEntryPoint("forja.workflows", "wf-other", callback)
    fake = _fake_entry_points([entry])
    monkeypatch.setattr(metadata, "entry_points", fake)
    monkeypatch.setattr(workflows, "entry_points", fake, raising=False)
    workflows.load_entry_points("forja.outros")
    assert "wf-other" not in workflows.WORKFLOWS


def test_load_entry_points_tolerates_no_plugins(monkeypatch):
    from importlib import metadata

    from forja import workflows

    before = set(workflows.WORKFLOWS)
    fake = _fake_entry_points([])
    monkeypatch.setattr(metadata, "entry_points", fake)
    monkeypatch.setattr(workflows, "entry_points", fake, raising=False)
    workflows.load_entry_points("forja.workflows")
    assert set(workflows.WORKFLOWS) == before
