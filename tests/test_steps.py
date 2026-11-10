"""Contratos de forja.steps descritos no DESIGN.md."""
import json

import pytest


def _ctx(steps, tmp_path, dry_run=False):
    return steps.Ctx(
        root=tmp_path,
        cfg={},
        work=tmp_path / "work",
        out=tmp_path / "out",
        env={},
        log=lambda message: None,
        dry_run=dry_run,
    )


def _step(steps, name, path, calls, needs=None, inputs=None):
    def step_inputs(ctx):
        if inputs is not None:
            return inputs(ctx)
        return [], {}

    def step_outputs(ctx):
        return [path]

    def run(ctx):
        calls.append(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
        return None

    return steps.Step(
        name=name,
        doc="passo " + name,
        inputs=step_inputs,
        outputs=step_outputs,
        run=run,
        needs=list(needs or []),
    )


def test_ctx_exposes_documented_fields(tmp_path):
    from forja import steps

    log = lambda message: None
    ctx = steps.Ctx(
        root=tmp_path,
        cfg={"a": 1},
        work=tmp_path / "work",
        out=tmp_path / "out",
        env={"X": "1"},
        log=log,
        dry_run=True,
    )
    assert (
        ctx.root,
        ctx.cfg,
        ctx.work,
        ctx.out,
        ctx.env,
        ctx.log,
        ctx.dry_run,
    ) == (tmp_path, {"a": 1}, tmp_path / "work", tmp_path / "out", {"X": "1"}, log, True)


def test_step_exposes_documented_fields(tmp_path):
    from forja import steps

    step = _step(steps, "A", tmp_path / "a.txt", [], needs=["B"])
    assert (
        step.name,
        step.doc,
        step.needs,
        callable(step.inputs),
        callable(step.outputs),
        callable(step.run),
    ) == ("A", "passo A", ["B"], True, True, True)


def test_run_steps_executes_steps_in_given_order(tmp_path):
    from forja import steps

    calls = []
    a = _step(steps, "A", tmp_path / "a.txt", calls)
    b = _step(steps, "B", tmp_path / "b.txt", calls)
    result = steps.run_steps(_ctx(steps, tmp_path), [a, b])
    assert (calls, [entry["step"] for entry in result]) == (["A", "B"], ["A", "B"])


def test_run_steps_result_has_documented_shape(tmp_path):
    from forja import steps

    out = tmp_path / "a.txt"
    result = steps.run_steps(_ctx(steps, tmp_path), [_step(steps, "A", out, [])])
    entry = result[0]
    assert (
        set(entry) == {"step", "status", "ms", "outputs"}
        and entry["step"] == "A"
        and entry["status"] == "ok"
        and isinstance(entry["ms"], (int, float))
        and entry["outputs"]
        and all(isinstance(path, str) for path in entry["outputs"])
        and entry["outputs"][0].endswith("a.txt")
    )


def test_run_steps_skips_fresh_step(tmp_path):
    from forja import steps

    calls = []
    ctx = _ctx(steps, tmp_path)
    step = _step(steps, "A", tmp_path / "a.txt", calls)
    first = steps.run_steps(ctx, [step])
    second = steps.run_steps(ctx, [step])
    assert (calls, first[0]["status"], second[0]["status"]) == (["A"], "ok", "skipped")


def test_run_steps_force_reruns_fresh_step(tmp_path):
    from forja import steps

    calls = []
    ctx = _ctx(steps, tmp_path)
    step = _step(steps, "A", tmp_path / "a.txt", calls)
    steps.run_steps(ctx, [step])
    forced = steps.run_steps(ctx, [step], force=True)
    assert (calls, forced[0]["status"]) == (["A", "A"], "ok")


def test_run_steps_reruns_when_input_changes(tmp_path):
    from forja import steps

    source = tmp_path / "in.txt"
    source.write_text("one", encoding="utf-8")
    calls = []
    step = _step(
        steps,
        "A",
        tmp_path / "a.txt",
        calls,
        inputs=lambda ctx: ([source], {}),
    )
    ctx = _ctx(steps, tmp_path)
    steps.run_steps(ctx, [step])
    source.write_text("two", encoding="utf-8")
    steps.run_steps(ctx, [step])
    assert calls == ["A", "A"]


def test_run_steps_reruns_when_output_is_missing(tmp_path):
    from forja import steps

    out = tmp_path / "a.txt"
    calls = []
    step = _step(steps, "A", out, calls)
    ctx = _ctx(steps, tmp_path)
    steps.run_steps(ctx, [step])
    out.unlink()
    steps.run_steps(ctx, [step])
    assert calls == ["A", "A"]


def test_run_steps_only_runs_selected_step_and_keeps_fresh_needs(tmp_path):
    from forja import steps

    calls = []
    a = _step(steps, "A", tmp_path / "a.txt", calls)
    b = _step(steps, "B", tmp_path / "b.txt", calls, needs=["A"])
    ctx = _ctx(steps, tmp_path)
    steps.run_steps(ctx, [a, b], only=["A"])
    result = steps.run_steps(ctx, [a, b], only=["B"])
    assert (calls, [entry["step"] for entry in result]) == (["A", "B"], ["B"])


def test_run_steps_missing_need_raises_missing_input(tmp_path):
    from forja import errors, steps

    b = _step(steps, "B", tmp_path / "b.txt", [], needs=["A"])
    with pytest.raises(errors.ForjaError) as excinfo:
        steps.run_steps(_ctx(steps, tmp_path), [b], only=["B"])
    assert excinfo.value.code == "MISSING_INPUT"


def test_run_steps_unknown_only_name_is_a_usage_error(tmp_path):
    from forja import errors, steps

    a = _step(steps, "A", tmp_path / "a.txt", [])
    with pytest.raises(errors.ForjaError) as excinfo:
        steps.run_steps(_ctx(steps, tmp_path), [a], only=["nao-existe"])
    assert excinfo.value.exit_code == 2


def test_run_steps_emits_started_ok_and_skipped_events(tmp_path):
    from forja import events, steps

    ctx = _ctx(steps, tmp_path)
    step = _step(steps, "A", tmp_path / "a.txt", [])
    steps.run_steps(ctx, [step])
    steps.run_steps(ctx, [step])
    assert [event["status"] for event in events.read_events(ctx.work)] == [
        "started",
        "ok",
        "skipped",
    ]


def test_run_steps_failure_emits_failed_and_reraises(tmp_path):
    from forja import errors, events, steps

    def run(ctx):
        raise errors.ForjaError("PROVIDER_ERROR", "falhou")

    step = steps.Step(
        name="A",
        doc="falha",
        inputs=lambda ctx: ([], {}),
        outputs=lambda ctx: [],
        run=run,
        needs=[],
    )
    ctx = _ctx(steps, tmp_path)
    with pytest.raises(errors.ForjaError) as excinfo:
        steps.run_steps(ctx, [step])
    last = events.read_events(ctx.work)[-1]
    assert (excinfo.value.code, last["step"], last["status"]) == (
        "PROVIDER_ERROR",
        "A",
        "failed",
    )


def test_run_steps_stops_after_a_failure(tmp_path):
    from forja import errors, steps

    def boom(ctx):
        raise errors.ForjaError("INTERNAL", "boom")

    a = steps.Step(
        name="A",
        doc="falha",
        inputs=lambda ctx: ([], {}),
        outputs=lambda ctx: [],
        run=boom,
        needs=[],
    )
    calls = []
    b = _step(steps, "B", tmp_path / "b.txt", calls)
    with pytest.raises(errors.ForjaError):
        steps.run_steps(_ctx(steps, tmp_path), [a, b])
    assert calls == []


def test_run_steps_dry_run_does_not_run_or_write(tmp_path):
    from forja import steps

    calls = []
    ctx = _ctx(steps, tmp_path, dry_run=True)
    result = steps.run_steps(ctx, [_step(steps, "A", tmp_path / "a.txt", calls)])
    assert (
        calls == []
        and result[0]["status"] == "would_run"
        and not (ctx.work / "manifest.json").exists()
        and not (ctx.work / "events.ndjson").exists()
    )


def test_run_steps_dry_run_reports_fresh_as_skipped(tmp_path):
    from forja import steps

    calls = []
    step = _step(steps, "A", tmp_path / "a.txt", calls)
    steps.run_steps(_ctx(steps, tmp_path), [step])
    result = steps.run_steps(_ctx(steps, tmp_path, dry_run=True), [step])
    assert (calls, result[0]["status"]) == (["A"], "skipped")


def test_run_steps_with_no_steps_returns_empty_list(tmp_path):
    from forja import steps

    assert steps.run_steps(_ctx(steps, tmp_path), []) == []


def test_run_steps_writes_readable_manifest_json(tmp_path):
    from forja import steps

    ctx = _ctx(steps, tmp_path)
    steps.run_steps(ctx, [_step(steps, "A", tmp_path / "a.txt", [])])
    manifest = ctx.work / "manifest.json"
    assert manifest.is_file() and isinstance(
        json.loads(manifest.read_text(encoding="utf-8")), dict
    )
