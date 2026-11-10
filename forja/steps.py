from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping

from .cache import Manifest, hash_inputs
from .errors import ForjaError
from .events import emit


@dataclass
class Step:
    """Um passo idempotente de um workflow."""

    name: str
    doc: str
    inputs: Callable[[Ctx], tuple[list[Path], dict]]
    outputs: Callable[[Ctx], list[Path]]
    run: Callable[[Ctx], dict | None]
    needs: list[str] = field(default_factory=list)


@dataclass
class Ctx:
    """Contexto de execucao compartilhado pelos passos."""

    root: Path
    cfg: dict
    work: Path
    out: Path
    env: Mapping
    log: Callable[[str], None]
    dry_run: bool


def _manifest_path(ctx: Ctx) -> Path:
    return Path(ctx.work) / "manifest.json"


def _inspect(ctx: Ctx, step: Step, manifest: Manifest) -> tuple[str, list[Path], bool]:
    """Calcula hash das entradas e a frescura do passo."""
    inputs = step.inputs(ctx)
    paths, extra = inputs
    outputs = [Path(path) for path in step.outputs(ctx)]
    digest = hash_inputs(paths, extra)
    return digest, outputs, manifest.is_fresh(step.name, digest, outputs)


def _select(ctx: Ctx, steps: list[Step], only: list[str], force: bool) -> list[Step]:
    """Resolve ``only`` para os passos pedidos mais dependencias nao frescas."""
    by_name = {step.name: step for step in steps}
    for name in only:
        if name not in by_name:
            raise ForjaError(
                "USAGE",
                f"passo desconhecido: {name}",
                details={"only": list(only), "steps": list(by_name)},
            )

    manifest = Manifest(_manifest_path(ctx))
    requested = set(only)
    selected: list[Step] = []
    selected_names: set[str] = set()
    visiting: set[str] = set()
    freshness: dict[str, bool] = {}

    def is_fresh(step: Step) -> bool:
        if step.name not in freshness:
            _, _, fresh = _inspect(ctx, step, manifest)
            freshness[step.name] = fresh
        return freshness[step.name]

    def visit(step: Step) -> None:
        if step.name in selected_names:
            return
        if step.name in visiting:
            raise ForjaError(
                "CONFIG_INVALID", f"dependencia circular no passo {step.name}"
            )
        visiting.add(step.name)
        for need_name in step.needs:
            need = by_name.get(need_name)
            if need is None:
                raise ForjaError(
                    "MISSING_INPUT",
                    f"passo dependente ausente: {need_name}",
                    details={"step": step.name, "need": need_name},
                )
            if force or not is_fresh(need):
                visit(need)
        visiting.discard(step.name)
        selected.append(step)
        selected_names.add(step.name)

    for step in steps:
        if step.name in requested:
            visit(step)
    return selected


def _output_strings(outputs: list[Path]) -> list[str]:
    return [str(output) for output in outputs]


def _error_fields(exc: Exception) -> dict:
    if isinstance(exc, ForjaError):
        return {"code": exc.code, "msg": exc.msg}
    return {"code": "INTERNAL", "msg": str(exc)}


def run_steps(ctx: Ctx, steps, only=None, force=False) -> list[dict]:
    """Executa passos em ordem, pulando os frescos e registrando eventos."""
    step_list = list(steps)
    if only is None:
        selected = step_list
    else:
        selected = _select(ctx, step_list, list(only), force)

    if not selected:
        return []

    manifest = Manifest(_manifest_path(ctx))
    results: list[dict] = []
    for step in selected:
        digest, outputs, fresh = _inspect(ctx, step, manifest)
        if fresh and not force:
            if not ctx.dry_run:
                emit(ctx.work, step.name, "skipped")
            results.append(
                {
                    "step": step.name,
                    "status": "skipped",
                    "ms": 0.0,
                    "outputs": _output_strings(outputs),
                }
            )
            continue
        if ctx.dry_run:
            results.append(
                {
                    "step": step.name,
                    "status": "would_run",
                    "ms": 0.0,
                    "outputs": _output_strings(outputs),
                }
            )
            continue

        emit(ctx.work, step.name, "started")
        started = time.perf_counter()
        try:
            step.run(ctx)
        except Exception as exc:
            elapsed = round((time.perf_counter() - started) * 1000, 3)
            emit(
                ctx.work,
                step.name,
                "failed",
                ms=elapsed,
                error=_error_fields(exc),
            )
            if isinstance(exc, ForjaError):
                raise
            raise ForjaError("INTERNAL", str(exc)) from exc

        elapsed = round((time.perf_counter() - started) * 1000, 3)
        manifest.put(step.name, digest, outputs)
        manifest.save()
        emit(ctx.work, step.name, "ok", ms=elapsed)
        results.append(
            {
                "step": step.name,
                "status": "ok",
                "ms": elapsed,
                "outputs": _output_strings(outputs),
            }
        )
    return results
