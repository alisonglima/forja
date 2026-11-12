from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from . import (
    __version__,
    approvals as approvals_module,
    brief,
    config,
    describe as describe_module,
    events as events_module,
    media,
    probe,
    project as project_module,
    env as env_module,
    registry,
    steps as steps_module,
    workflows,
)
from .errors import ForjaError, error_payload

# Fluxos injetados por ``main``; nunca escrevemos em sys.stdout direto.
_STREAMS = {"out": sys.stdout, "err": sys.stderr}

_STEP_COMMANDS = {"transcribe", "check", "voices", "schedule", "mix", "render", "qa"}
_STATUS_LABELS = {"ok": "ok", "skipped": "pulado", "would_run": "executaria", "failed": "falhou"}


class _UsageError(Exception):
    """Erro de uso detectado antes/durante o argparse."""


def _stream_write(stream, text):
    stream.write(text)
    if text and not text.endswith("\n"):
        stream.write("\n")


def _one_line(text):
    return " ".join(str(text).splitlines()).strip()


def _json_text(payload):
    return json.dumps(payload, ensure_ascii=False, default=str)


class _Parser(argparse.ArgumentParser):
    """ArgumentParser que nao imprime nem chama sys.exit por conta propria."""

    def error(self, message):
        raise _UsageError(message)

    def exit(self, status=0, message=None):
        if message:
            _stream_write(_STREAMS["err"], message)
        raise SystemExit(status)

    def _print_message(self, message, file=None):
        if message:
            target = _STREAMS["err"] if file is sys.stderr else _STREAMS["out"]
            _stream_write(target, message)


def _build_parser():
    parser = _Parser(
        prog="forja",
        description="Plataforma de geracao de video operada por agentes.",
        add_help=False,
        exit_on_error=False,
    )
    sub = parser.add_subparsers(dest="command", metavar="comando")
    sub.required = True

    def command(name):
        return sub.add_parser(name, add_help=False, exit_on_error=False)

    approve = command("approve")
    approve.add_argument("--slides", action="store_true")
    approve.add_argument("--script", action="store_true")
    approve.add_argument("--voice", action="store_true")
    approve.add_argument("--overlays", action="store_true")
    approve.add_argument("--publish", action="store_true")
    approve.add_argument("--brief", action="store_true")
    approve.add_argument("--post", action="store_true")
    approve.add_argument("--hash", action="append", default=None)
    approve.add_argument("--by", default=None)

    slides = command("slides")
    slides.add_argument("--deck", default="deck.yaml")
    slides.add_argument("--template", default=None)
    slides.add_argument("--sources", default=None)
    slides.add_argument("--out", default="out")
    slides.add_argument("--only", default=None)
    slides.add_argument("--force", action="store_true")
    slides.add_argument("--captures", default="1280,360")

    deliver = command("deliver")
    deliver.add_argument("--post", action="store_true")
    deliver.add_argument("--by", default=None)
    deliver.add_argument("--confirm", action="store_true")

    init = command("init")
    init.add_argument("dir")
    init.add_argument("--source", default=None)
    init.add_argument("--force", action="store_true")
    init.add_argument("--workflow", default=None)
    init.add_argument("--no-require-approvals", action="store_true")

    for name in ("describe", "status", "doctor", "providers", "transcribe", "check", "schedule", "mix", "render"):
        command(name)

    run = command("run")
    run.add_argument("--only", default=None)
    run.add_argument("--force", action="store_true")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--strict", action="store_true")

    frames = command("frames")
    frames.add_argument("--every", type=float, default=2.0)

    voices = command("voices")
    voices.add_argument("--only", default=None)
    voices.add_argument("--force", action="store_true")

    qa = command("qa")
    qa.add_argument("--strict", action="store_true")

    mcp = command("mcp")
    mcp.add_argument("action", choices=("serve",))
    return parser


def _split_globals(argv):
    """Retira --json/--project de qualquer posicao (antes ou depois do comando)."""
    rest, json_mode, project_dir, index = [], False, ".", 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--json":
            json_mode = True
        elif arg == "--project":
            if index + 1 >= len(argv):
                raise _UsageError("--project exige um diretorio")
            project_dir = argv[index + 1]
            index += 1
        elif arg.startswith("--project="):
            project_dir = arg[len("--project="):]
            if not project_dir:
                raise _UsageError("--project exige um diretorio")
        else:
            rest.append(arg)
        index += 1
    return rest, json_mode, project_dir


def _envelope(data, next_actions=None, artifacts=None, warnings=None):
    return {
        "ok": True,
        "data": data,
        "next_actions": list(next_actions or []),
        "artifacts": list(artifacts or []),
        "warnings": list(warnings or []),
        "cost": None,
    }


def _fail(exc, json_mode, out, err):
    if not isinstance(exc, ForjaError):
        exc = ForjaError("INTERNAL", str(exc))
    if json_mode:
        _stream_write(out, _json_text(error_payload(exc)))
    else:
        message = "forja: " + _one_line(exc.msg)
        hint = _one_line(exc.hint)
        if hint:
            message += " - " + hint
        _stream_write(err, message)
    return exc.exit_code


def _write_json(out, payload):
    _stream_write(out, _json_text(payload))


def _write_warnings(warnings, err):
    for warning in warnings or []:
        _stream_write(err, "aviso: " + _one_line(warning))


def _parse_only(value):
    if value is None:
        return None
    names = [part.strip() for part in str(value).split(",") if part.strip()]
    if not names:
        raise _UsageError("--only exige ao menos um nome")
    return names


def _require_project(project_dir):
    project = project_module.Project(project_dir)
    if not project.root.exists():
        raise ForjaError("CONFIG_INVALID", "projeto nao encontrado: %s" % project.root, hint="rode `forja init DIR --source VIDEO` para criar o projeto")
    if not project.config_path.is_file():
        raise ForjaError("CONFIG_INVALID", "config.yaml nao encontrado em %s" % project.root, hint="rode `forja init DIR --source VIDEO` para criar o projeto")
    return project


def _load_config(project):
    try:
        return project.load_config()
    except config.ConfigError as exc:
        raise ForjaError("CONFIG_INVALID", str(exc), details={"path": str(project.config_path)}) from exc
    except yaml.YAMLError as exc:
        raise ForjaError("CONFIG_INVALID", "config.yaml invalido: %s" % exc, details={"path": str(project.config_path)}) from exc
    except FileNotFoundError as exc:
        raise ForjaError("CONFIG_INVALID", "config.yaml nao encontrado: %s" % project.config_path) from exc
    except OSError as exc:
        raise ForjaError("CONFIG_INVALID", str(exc)) from exc


def _optional_config(root):
    """Config para o doctor: defaults quando o projeto (ou config) nao existe."""
    project = project_module.Project(root)
    if not project.config_path.is_file():
        return project, copy.deepcopy(config.DEFAULTS), False, "config.yaml ausente (usando defaults)"
    try:
        return project, project.load_config(), True, "config.yaml ok"
    except Exception as exc:  # doctor continua mesmo com config quebrada
        return project, copy.deepcopy(config.DEFAULTS), False, _one_line(exc)


def _project_workflow(root, cfg=None, override=None):
    if override:
        return str(override)
    if isinstance(cfg, dict) and isinstance(cfg.get("project"), dict):
        name = cfg["project"].get("workflow")
        if name:
            return str(name)
    if (Path(root) / "storyboard.yaml").is_file():
        return "storyboard"
    return "dub"


def _workflow_steps(name):
    return list(workflows.get_workflow(name).steps_factory())


def _make_ctx(project, cfg, env, err, dry_run=False):
    def log(message):
        text = _one_line(message)
        if text:
            _stream_write(err, text)

    return steps_module.Ctx(root=project.root, cfg=cfg, work=project.work, out=project.out, env=env, log=log, dry_run=dry_run)


def _run_selected(project, cfg, env, err, only, force, dry_run, only_cues=None):
    workflow = _project_workflow(project.root, cfg)
    ctx = _make_ctx(project, cfg, env, err, dry_run=dry_run)
    if only_cues is not None:
        # Campo extra lido por implementacoes futuras do passo voices.
        ctx.only_cues = only_cues
    results = steps_module.run_steps(ctx, _workflow_steps(workflow), only=only, force=force)
    return results, ctx


def _read_json(path, what=None):
    path = Path(path)
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError) as exc:
        if what:
            raise ForjaError(
                "GATE_FAILED",
                "%s ilegivel: %s" % (what, path),
                hint="rode o passo de novo para regerar o arquivo",
                details={"path": str(path), "error": str(exc)},
            ) from exc
        return None


def _issues(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("issues"), list):
        return payload["issues"]
    return []


def _errors(issues):
    return [issue for issue in issues if isinstance(issue, dict) and issue.get("level") == "error"]


def _gate_check(project, results, strict):
    errors = _errors(_issues(_read_json(project.work / "check.json", "check.json")))
    if not errors:
        return []
    if strict:
        raise ForjaError("GATE_FAILED", "check reprovado: %d erro(s)" % len(errors), details={"steps": results, "issues": errors})
    return ["check: %d erro(s)" % len(errors)]


def _qa_failed(payload):
    if isinstance(payload, dict) and payload.get("ok") is False:
        return True
    return bool(_errors(_issues(payload)))


def _gate_qa(project, results, strict):
    payload = _read_json(project.out / "qa.json", "qa.json")
    if not _qa_failed(payload):
        return []
    if strict:
        raise ForjaError("GATE_FAILED", "QA reprovado", details={"steps": results, "issues": _errors(_issues(payload))})
    return ["QA reprovado (use --strict para falhar)"]


def _results_text(results):
    lines = []
    for result in results or []:
        line = "%s: %s" % (_STATUS_LABELS.get(result.get("status", ""), result.get("status", "")), result.get("step", "?"))
        outputs = result.get("outputs") or []
        if outputs:
            line += " -> " + ", ".join(str(output) for output in outputs)
        lines.append(line)
    return lines


def _artifacts_from(results):
    return [{"path": str(output), "kind": "file"} for result in results or [] for output in result.get("outputs") or []]


def _cmd_describe(json_mode, out):
    document = describe_module.describe(workflows.WORKFLOWS, __version__)
    if json_mode:
        _write_json(out, _envelope(document))
        return 0
    commands = [item.get("name", "") for item in document.get("commands", [])]
    lines = [
        "forja %s" % document.get("version", ""),
        "comandos: " + ", ".join(commands),
        "workflows: " + ", ".join(sorted(document.get("workflows", {}))),
        "provedores: %d" % len(document.get("providers", [])),
    ]
    _stream_write(out, "\n".join(lines))
    return 0


def _scaffold(args):
    root = Path(args.dir).expanduser()
    name = root.name or root.resolve().name
    # Sem --workflow: com video de origem e dublagem; sem video, e um projeto por cenas.
    workflow = _project_workflow(root, override=args.workflow or ("dub" if args.source else "storyboard"))
    workflows.get_workflow(workflow)  # valida antes de criar qualquer coisa
    if workflow == "dub" and not args.source:
        raise ForjaError("USAGE", "o workflow dub precisa de --source VIDEO", hint="`forja init DIR --source VIDEO` (ou `--workflow storyboard` para um video por cenas, sem origem)")
    created = project_module.scaffold(
        root,
        name,
        source=args.source,
        workflow=workflow,
        force=bool(args.force),
        require_approvals=not bool(getattr(args, "no_require_approvals", False)),
    )
    return root, created


def _cmd_init(args, json_mode, out):
    root, created = _scaffold(args)
    if json_mode:
        _write_json(
            out,
            _envelope(
                {"created": created},
                next_actions=[{"command": "forja --project %s status" % shlex.quote(str(root)), "why": "confira o estado inicial do projeto"}],
                artifacts=[{"path": path, "kind": "created"} for path in created],
            ),
        )
    else:
        _stream_write(out, "\n".join(["projeto criado em %s" % root] + ["  " + str(path) for path in created]))
    return 0


def _cmd_status(project_dir, json_mode, out):
    project = _require_project(project_dir)
    cfg = _load_config(project)
    workflow = _project_workflow(project.root, cfg)
    document = project_module.status(project, _workflow_steps(workflow))
    document["workflow"] = workflow
    if json_mode:
        next_action = document.get("next")
        _write_json(out, _envelope(document, next_actions=[next_action] if next_action else []))
        return 0
    lines = ["projeto: %s (%s)" % (document.get("project"), workflow)]
    for entry in document.get("steps", []):
        lines.append("  %s: %s - %s" % (entry.get("name"), entry.get("state"), entry.get("reason")))
    next_action = document.get("next")
    if next_action:
        lines.extend(["proximo: %s" % next_action.get("command"), "porque: %s" % next_action.get("why")])
    else:
        lines.append("proximo: nada; tudo atualizado")
    _stream_write(out, "\n".join(lines))
    return 0


_APPROVAL_CHUNK = 1024 * 1024


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(_APPROVAL_CHUNK):
            digest.update(block)
    return digest.hexdigest()


def _project_artifact(root, value):
    root = Path(root)
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        raise ForjaError("USAGE", "arquivo fora do projeto: %s" % value) from None
    if not path.is_file():
        raise ForjaError("MISSING_INPUT", "arquivo nao encontrado: %s" % relative, details={"path": relative})
    return path, relative


def _brief_sha256(root, data):
    try:
        return approvals_module.hash_brief(root)
    except ForjaError as exc:
        if exc.code != "MISSING_INPUT":
            raise
    return hashlib.sha256(_canonical(data).encode("utf-8")).hexdigest()


def _approval_stale(expected, current, piece, path):
    return ForjaError(
        "APPROVAL_STALE",
        "aprovacao por hash invalida ou desatualizada",
        details={"expected": expected, "current": current, "piece": piece, "path": path},
    )


def _save_approvals(root, data):
    path = brief.approvals_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _cmd_approve_slides(project_dir, args, json_mode, out):
    """Aprova um deck pelo hash de cada artefato; falha fechada sem --by."""
    project = _require_project(project_dir)
    by = (args.by or "").strip()
    if not by:
        raise ForjaError("USAGE", "informe quem aprovou em --by", hint="ex.: forja approve --slides --hash out/deck.pptx --hash out/deck.pdf --by Ana")
    values = list(args.hash or [])
    if len(values) < 2:
        raise ForjaError("USAGE", "informe --hash para cada artefato (pptx e pdf)", hint="ex.: forja approve --slides --hash out/deck.pptx --hash out/deck.pdf --by Ana")
    data = brief.load_approvals(project.root)
    records = []
    for value in values:
        path, relative = _project_artifact(project.root, value)
        records.append({"path": relative, "sha256": _file_sha256(path), "bytes": path.stat().st_size})
    records.sort(key=lambda item: item["path"])
    updates = {key: bool(data.get(key)) for key in brief.APPROVAL_KEYS}
    saved = brief.write_approvals(project.root, updates, by=by)
    saved["schema_version"] = 2
    saved["artifacts"] = records
    _save_approvals(project.root, saved)
    if json_mode:
        _write_json(out, _envelope({"approvals": saved, "path": brief.APPROVALS_FILE}))
        return 0
    _stream_write(out, "artefatos aprovados: %d por %s" % (len(records), saved["by"]))
    return 0


def _cmd_approve(project_dir, args, json_mode, out):
    if getattr(args, "slides", False):
        return _cmd_approve_slides(project_dir, args, json_mode, out)
    project = _require_project(project_dir)
    updates = {
        key: True
        for key in ("script", "voice", "overlays", "publish")
        if getattr(args, key, False)
    }
    if not (updates or args.post or args.brief or args.hash):
        raise ForjaError(
            "USAGE",
            "informe ao menos uma aprovacao (--script, --voice, --overlays, --publish, --brief, --post ou --hash)",
            hint="ex.: forja approve --script --voice --by Ana",
        )
    by = "humano" if args.by is None else args.by.strip()
    if not by or (args.post and args.by is None):
        raise ForjaError(
            "USAGE",
            "informe quem aprovou em --by",
            hint="ex.: forja approve --post --hash out/peca.png --by Ana",
        )
    data = brief.load_approvals(project.root)
    brief_data = None
    if args.brief or args.post or args.hash:
        brief_data = brief.load_brief(project.root)
        if brief_data is None:
            raise ForjaError("MISSING_INPUT", "brief.yaml ausente: sem brief nao ha o que aprovar")
        if args.brief:
            issues = [item for item in brief.brief_issues(project.root) if item.get("code") == "BRIEF_INCOMPLETE"]
            if issues:
                raise ForjaError("BRIEF_INCOMPLETE", issues[0].get("msg") or "brief incompleto")
    records, block = [], None
    if args.hash:
        for value in args.hash:
            path, relative = _project_artifact(project.root, value)
            records.append({"path": relative, "sha256": _file_sha256(path), "bytes": path.stat().st_size})
        records.sort(key=lambda item: item["path"])
        current = records[0]["sha256"] if len(records) == 1 else hashlib.sha256(_canonical(records).encode("utf-8")).hexdigest()
        piece = brief_data.get("piece")
        path = records[0]["path"]
        stored = data.get("hash")
        expected = stored.get("valor") if isinstance(stored, dict) else None
        if expected is not None and expected != current:
            raise _approval_stale(expected, current, piece or data.get("piece"), path)
        block = {"algoritmo": "sha256", "valor": current}
        if len(records) == 1:
            block["arquivo"] = path
            block["bytes"] = records[0]["bytes"]
    if not updates:
        updates = {key: bool(data.get(key)) for key in brief.APPROVAL_KEYS}
    saved = brief.write_approvals(project.root, updates, by=by)
    if brief_data is not None:
        for key in ("piece", "brand_id", "format"):
            value = brief_data.get(key)
            if isinstance(value, str) and value.strip():
                saved[key] = value
        saved["schema_version"] = 2
    if args.brief:
        saved["brief"] = {"sha256": _brief_sha256(project.root, brief_data), "by": saved["by"], "at": saved["at"]}
    if block is not None:
        saved["artifacts"] = records
        saved["hash"] = block
    if brief_data is not None or block is not None:
        _save_approvals(project.root, saved)
    if json_mode:
        _write_json(out, _envelope({"approvals": saved, "path": brief.APPROVALS_FILE, "brief": saved.get("brief"), "hash": saved.get("hash")}))
        return 0
    _stream_write(out, "aprovacoes registradas: " + ", ".join(sorted(updates)) + " por " + saved["by"])
    return 0


_DELIVER_FILES = ("manifest.json", "legenda.txt", "hashtags.txt", "alt.txt", "horario.json", "manifesto-ia.json")


def _load_estado(root):
    path = Path(root) / "work" / "estado.json"
    if not path.is_file(): return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ForjaError("GATE_FAILED", "estado ilegivel: %s" % exc) from exc
    if not isinstance(data, dict) or not isinstance(data.get("estado"), str):
        raise ForjaError("GATE_FAILED", "estado invalido; a entrega falha fechada")
    return data


def _save_estado(root, data):
    path = Path(root) / "work" / "estado.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _stale_details(piece, path=None, expected=None, current=None):
    return {"expected": expected, "current": current, "piece": piece, "path": path}


def _deliver_approval(root, approvals, piece):
    record = approvals.get("hash")
    label = record.get("arquivo") if isinstance(record, dict) else None
    if not isinstance(label, str) or not label.strip():
        raise ForjaError("APPROVAL_STALE", "aprovacao sem hash/arquivo final", details=_stale_details(piece))
    root = Path(root)
    target = (root / label).resolve()
    try:
        relative = target.relative_to(root.resolve()).as_posix()
    except ValueError:
        raise ForjaError("APPROVAL_STALE", "artefato aprovado fora do projeto: %s" % label,
                         details=_stale_details(piece, label, record.get("valor"))) from None
    expected = record.get("valor")
    current = _file_sha256(target) if target.is_file() else None
    if not isinstance(expected, str) or not expected or current != expected:
        raise _approval_stale(expected, current, piece, relative)
    return target, relative, current, record


def _deliver_package(root, piece):
    package = Path(root) / "out" / piece
    manifest_path = package / "manifest.json"
    if not manifest_path.is_file(): raise ForjaError("ASSET_MISSING", "pacote sem manifest.json: %s" % package.as_posix())
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ForjaError("ASSET_MISSING", "manifest.json do pacote ilegivel: %s" % exc) from exc
    if not isinstance(manifest, dict): raise ForjaError("ASSET_MISSING", "manifest.json do pacote deve ser um objeto")
    names = list(_DELIVER_FILES)
    names.extend(item for item in manifest.get("arquivos") or () if isinstance(item, str))
    for name in names:
        if Path(name).name != name or not (package / name).is_file():
            raise ForjaError("ASSET_MISSING", "pacote incompleto: falta %s" % name, details={"path": name})
    return package


def _deliver_out(data, text, json_mode, out, **extra):
    if json_mode: _write_json(out, _envelope(data, **extra))
    else: _stream_write(out, text)


def _cmd_deliver(args, project_dir, json_mode, out):
    by = "" if args.by is None else args.by.strip()
    if not by:
        raise ForjaError("USAGE", "informe quem entregou em --by", hint="ex.: forja deliver --post --by Ana --confirm")
    project = _require_project(project_dir)
    root = project.root
    approvals = brief.load_approvals(root)
    estado = _load_estado(root)
    if estado is None or estado["estado"] not in ("aprovado", "entregue"):
        raise ForjaError("GATE_FAILED", "estado ausente ou invalido para entrega", hint="a peca precisa estar aprovada")
    piece = (brief.load_brief(root) or {}).get("piece") or approvals.get("piece") or estado.get("piece")
    if not isinstance(piece, str) or not piece.strip() or Path(piece).name != piece:
        raise ForjaError("MISSING_INPUT", "brief sem piece para entregar")
    pacote = (Path(root) / "out" / piece).relative_to(root).as_posix()
    if estado["estado"] == "entregue":
        data = {"estado": "entregue", "de": "aprovado", "para": "entregue", "pacote": pacote, "aprovacao": estado.get("aprovacao"), "artefato": estado.get("artefato")}
        _deliver_out(data, "peca ja entregue: %s" % pacote, json_mode, out)
        return 0
    target, relative, digest, record = _deliver_approval(root, approvals, piece)
    _deliver_package(root, piece)
    aprovacao = dict(estado.get("aprovacao") or {}, by=by, sha256=digest)
    aprovacao["at"] = aprovacao.get("at") or record.get("at") or ""
    artefato = estado.get("artefato")
    if not isinstance(artefato, dict):
        artefato = {"path": relative, "sha256": digest, "bytes": target.stat().st_size}
    if not args.confirm:
        data = {"estado": "aprovado", "de": None, "para": "entregue", "pacote": pacote, "aprovacao": aprovacao, "artefato": artefato}
        command = "forja deliver --project %s --post --by %s --confirm%s" % (shlex.quote(str(root)), shlex.quote(by), " --json" if json_mode else "")
        next_actions = [{"command": command, "why": "confirme a entrega do pacote aprovado"}]
        _deliver_out(data, "pronto para entregar: %s (rode de novo com --confirm)" % pacote, json_mode, out, next_actions=next_actions, artifacts=[artefato])
        return 0
    momento = events_module.emit(project.work, "deliver", "ok", by=by, de="aprovado", para="entregue", sha256=digest).get("t") or ""
    estado.setdefault("historico", []).append({"de": "aprovado", "para": "entregue", "por": by, "em": momento, "sha256": digest})
    estado.update({"estado": "entregue", "aprovacao": aprovacao})
    _save_estado(root, estado)
    data = {"estado": "entregue", "de": "aprovado", "para": "entregue", "pacote": pacote, "aprovacao": aprovacao, "artefato": artefato}
    _deliver_out(data, "entregue: %s por %s" % (pacote, by), json_mode, out, artifacts=[artefato])
    return 0


def _cmd_providers(json_mode, env, out):
    items = describe_module.builtin_providers(env) + registry.available(env=env)
    if json_mode:
        _write_json(out, _envelope(items))
        return 0
    lines = []
    for item in items:
        if item.get("error"):
            lines.append("%s: erro - %s" % (item.get("name"), item["error"]))
        else:
            lines.append("%s/%s: ambiente %s" % (item.get("kind"), item.get("name"), "ok" if item.get("env_ok") else "incompleto"))
    _stream_write(out, "\n".join(lines or ["nenhum provedor registrado"]))
    return 0


def _cmd_slides(args, project_dir, json_mode, env, out, err):
    """Roda o workflow slides; sem --template o deck falha antes de tudo."""
    template = (args.template or "").strip()
    if not template:
        raise ForjaError("DECK_TEMPLATE_MISSING", "informe --template: o deck exige um template do acervo", hint="ex.: forja slides --template lions-oficial-2022")
    project = _require_project(project_dir)
    cfg = _load_config(project)
    run_env = dict(env)
    if args.sources:
        sources = Path(args.sources).expanduser()
        run_env["FORJA_BRAND_SOURCES"] = str(sources if sources.is_absolute() else project.root / sources)
    ctx = _make_ctx(project, cfg, run_env, err)
    deck = Path(args.deck).expanduser()
    ctx.deck = deck if deck.is_absolute() else project.root / deck
    ctx.template = template
    try:
        ctx.captures = tuple(int(part.strip()) for part in args.captures.split(","))
    except ValueError:
        raise _UsageError("--captures deve ser LARGURA,ALTURA") from None
    if len(ctx.captures) != 2 or any(part <= 0 for part in ctx.captures):
        raise _UsageError("--captures deve ser LARGURA,ALTURA")
    target = Path(args.out).expanduser()
    ctx.out = target if target.is_absolute() else project.root / target
    ctx.out.mkdir(parents=True, exist_ok=True)
    results = steps_module.run_steps(ctx, _workflow_steps("slides"), only=_parse_only(args.only), force=bool(args.force))
    if json_mode:
        _write_json(out, _envelope({"steps": results, "deck": str(ctx.deck), "template": template, "captures": list(ctx.captures)}, artifacts=_artifacts_from(results)))
        return 0
    _stream_write(out, "\n".join(_results_text(results)))
    return 0


def _which(tool, env):
    search_path = env.get("PATH")
    return shutil.which(tool, path="" if search_path is None else search_path)


def _key_is_set(env, name):
    value = env.get(name)
    if value is None:
        return False
    return bool(value.strip()) if isinstance(value, str) else bool(value)


def _slides_doctor_checks(project_dir, env):
    """Checks de slides do doctor; detalhes nunca expoem caminho absoluto."""
    checks = []
    found = _which("soffice", env)
    checks.append(("soffice", found is not None, "encontrado no PATH" if found is not None else "nao encontrado no PATH"))
    base = Path(project_dir)
    source = env.get("FORJA_BRAND_SOURCES")
    root = Path(source).expanduser() if isinstance(source, str) and source.strip() else base / ".work" / "fontes" / "lions"
    index = next(iter(sorted(base.glob("brands/*/assets-index.json"))), None)
    if not root.is_dir():
        checks.append(("brand_sources", False, "raiz do acervo ausente: defina FORJA_BRAND_SOURCES"))
    elif index is None:
        checks.append(("brand_sources", False, "indice de ativos ausente em brands/"))
    else:
        checks.append(("brand_sources", True, "acervo ok: " + index.relative_to(base).as_posix()))
    deck_path = base / "deck.yaml"
    if not deck_path.is_file():
        checks.append(("pptx_template", False, "deck.yaml ausente: template nao conferido"))
        return checks
    try:
        deck = (yaml.safe_load(deck_path.read_text(encoding="utf-8")) or {}).get("deck") or {}
        catalog = json.loads((base / str(deck.get("modelo_catalogo") or "")).read_text(encoding="utf-8"))
        entry = next((item for item in catalog.get("templates") or [] if item.get("template_id") == deck.get("template")), None)
    except (OSError, ValueError, yaml.YAMLError, AttributeError, TypeError):
        checks.append(("pptx_template", False, "deck ou catalogo ilegivel: template nao conferido"))
        return checks
    template = deck.get("template")
    if entry is None or not isinstance(template, str) or not template.strip():
        checks.append(("pptx_template", False, "template do deck ausente no catalogo"))
    elif not isinstance(entry.get("file"), str) or not (root / entry["file"]).is_file():
        checks.append(("pptx_template", False, "arquivo do template ausente no acervo"))
    elif _file_sha256(root / entry["file"]) != entry.get("sha256"):
        checks.append(("pptx_template", False, "sha256 do template nao confere"))
    else:
        checks.append(("pptx_template", True, "template %s confere" % template))
    return checks


def _cmd_doctor(project_dir, json_mode, env, out, err):
    checks = []

    def add(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    _, cfg, config_ok, config_detail = _optional_config(project_dir)
    add("config", config_ok, config_detail)
    for tool in ("ffmpeg", "ffprobe", "node"):
        found = _which(tool, env)
        add(tool, found is not None, "encontrado" if found is not None else "nao encontrado no PATH")
    for library in ("numpy", "scipy", "yaml", "faster_whisper", "pptx"):
        try:
            spec = importlib.util.find_spec(library)
        except Exception:
            spec = None
        add("python:" + library, spec is not None, "importavel" if spec is not None else "nao instalada")
    for name, ok, detail in _slides_doctor_checks(project_dir, env):
        add(name, ok, detail)

    voices = cfg.get("voices") if isinstance(cfg, dict) else {}
    if not isinstance(voices, dict):
        voices = {}
    provider = str(voices.get("provider") or "files")
    if provider == "gemini":
        key_name = voices.get("api_key_env") or "GEMINI_API_KEY"
        key_ok = _key_is_set(env, key_name)
        # Apenas o NOME da variavel e o estado; o valor nunca entra na saida.
        add("tts_api_key", key_ok, "%s: %s" % (key_name, "definida" if key_ok else "ausente"))
    elif provider == "piper":
        piper = voices.get("piper") if isinstance(voices.get("piper"), dict) else {}
        binary = str(piper.get("binary") or "piper")
        model = str(piper.get("model") or "")
        found = _which(binary, env)
        model_ok = bool(model) and Path(model).is_file()
        add(
            "tts_provider",
            found is not None and model_ok,
            "provider: piper; binario %s; modelo %s"
            % ("ok" if found is not None else "ausente", "ok" if model_ok else "ausente"),
        )
    elif provider == "google_ai_studio":
        add("tts_provider", True, "provider: google_ai_studio (sem chave; WAVs em voices/)")
    else:
        add("tts_provider", True, "provider: %s (sem chave de API)" % provider)

    essential = {"ffmpeg", "ffprobe"}
    missing = [item["name"] for item in checks if item["name"] in essential and not item["ok"]]
    warnings = [
        "%s: %s" % (item["name"], item["detail"])
        for item in checks
        if not item["ok"] and item["name"] not in essential and item["name"] != "config"
    ]
    if missing:
        raise ForjaError("MISSING_PREREQ", "faltam pre-requisitos: " + ", ".join(missing), details={"checks": checks})
    if json_mode:
        _write_json(out, _envelope({"checks": checks}, warnings=warnings))
        return 0
    _stream_write(out, "\n".join(("ok: " if item["ok"] else "FALTA: ") + item["name"] + " - " + item["detail"] for item in checks))
    _write_warnings(warnings, err)
    return 0


def _cmd_run(args, project_dir, json_mode, env, out, err):
    project = _require_project(project_dir)
    cfg = _load_config(project)
    results, _ = _run_selected(project, cfg, env, err, only=_parse_only(args.only), force=bool(args.force), dry_run=bool(args.dry_run))
    warnings = []
    if not args.dry_run:
        warnings.extend(_gate_check(project, results, strict=bool(args.strict)))
        warnings.extend(_gate_qa(project, results, strict=bool(args.strict)))
    if json_mode:
        _write_json(out, _envelope({"steps": results}, artifacts=_artifacts_from(results), warnings=warnings))
        return 0
    _stream_write(out, "\n".join(_results_text(results)))
    _write_warnings(warnings, err)
    return 0


def _cmd_step(args, project_dir, json_mode, env, out, err):
    name = args.command
    project = _require_project(project_dir)
    cfg = _load_config(project)
    only_cues = _parse_only(getattr(args, "only", None)) if name == "voices" else None
    results, _ = _run_selected(
        project,
        cfg,
        env,
        err,
        only=[name],
        force=bool(getattr(args, "force", False)),
        dry_run=False,
        only_cues=only_cues,
    )
    warnings = []
    if name == "check":
        warnings.extend(_gate_check(project, results, strict=True))
    if name == "qa":
        warnings.extend(_gate_qa(project, results, strict=bool(args.strict)))
    if json_mode:
        _write_json(out, _envelope({"steps": results}, artifacts=_artifacts_from(results), warnings=warnings))
        return 0
    _stream_write(out, "\n".join(_results_text(results)))
    _write_warnings(warnings, err)
    return 0


def _cmd_frames(args, project_dir, json_mode, env, out):
    project = _require_project(project_dir)
    cfg = _load_config(project)
    every = float(args.every)
    if every <= 0:
        raise _UsageError("--every deve ser maior que zero")
    clip = project.work / "clip.mp4"
    if not clip.is_file():
        configured = (cfg.get("input") or {}).get("video") or "input/source.mp4"
        candidate = project.root / configured
        if not candidate.is_file():
            raise ForjaError("MISSING_INPUT", "video do projeto nao encontrado: %s" % candidate, hint="rode `forja run --only clip` ou confira input.video no config.yaml")
        clip = candidate
    ffmpeg = _which("ffmpeg", env)
    if ffmpeg is None:
        raise ForjaError("MISSING_PREREQ", "ffmpeg nao encontrado no PATH", hint="instale o ffmpeg e rode `forja doctor`")

    frames_dir = project.work / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for stale in list(frames_dir.glob("frame_*.jpg")) + list(frames_dir.glob("t*s.jpg")) + list(frames_dir.glob("contact.jpg")):
        stale.unlink()
    # Quadros reduzidos (640 px): suficientes para ler tarjas e rostos sem custar tokens de imagem.
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(clip), "-vf", "fps=1/%s,scale=640:-2" % every, str(frames_dir / "frame_%05d.jpg"), "-y"]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, env=env_module.sanitized(env))
    except FileNotFoundError as exc:
        raise ForjaError("MISSING_PREREQ", "ffmpeg nao encontrado: %s" % exc) from exc
    if completed.returncode != 0:
        tail = (completed.stderr or "").strip().splitlines()[-5:]
        raise ForjaError("PROVIDER_ERROR", "ffmpeg falhou ao extrair quadros", details={"stderr": "\n".join(tail)})

    # O n-esimo quadro (base 1) esta em (n-1)*every segundos: o tempo passa para o nome do arquivo.
    frames = []
    for index, path in enumerate(sorted(frames_dir.glob("frame_*.jpg"))):
        seconds = index * every
        target = frames_dir / ("t%06.1fs.jpg" % seconds)
        path.rename(target)
        frames.append({"path": str(target), "t": round(seconds, 3)})

    contact = None
    if frames:
        try:
            duration = float(probe.probe_video(clip)["duration"])
            count = min(16, len(frames))
            contact = str(media.contact_sheet(clip, frames_dir / "contact.jpg", duration, n=count, cols=4))
        except (ForjaError, RuntimeError, ValueError, KeyError, OSError):
            contact = None  # a folha de contato e uma conveniencia; os quadros ja bastam
    if json_mode:
        artifacts = [{"path": item["path"], "kind": "frame"} for item in frames]
        if contact:
            artifacts.append({"path": contact, "kind": "contact_sheet"})
        _write_json(out, _envelope({"frames": frames, "count": len(frames), "every": every, "contact_sheet": contact}, artifacts=artifacts))
        return 0
    _stream_write(out, "quadros extraidos: %d em %s%s" % (len(frames), frames_dir, " (folha de contato: contact.jpg)" if contact else ""))
    return 0


def _dispatch(args, project_dir, json_mode, env, out, err):
    command = args.command
    if command == "describe":
        return _cmd_describe(json_mode, out)
    if command == "init":
        return _cmd_init(args, json_mode, out)
    if command == "doctor":
        return _cmd_doctor(project_dir, json_mode, env, out, err)
    if command == "approve":
        return _cmd_approve(project_dir, args, json_mode, out)
    if command == "slides":
        return _cmd_slides(args, project_dir, json_mode, env, out, err)
    if command == "deliver":
        return _cmd_deliver(args, project_dir, json_mode, out)
    if command == "providers":
        return _cmd_providers(json_mode, env, out)
    if command == "status":
        return _cmd_status(project_dir, json_mode, out)
    if command == "run":
        return _cmd_run(args, project_dir, json_mode, env, out, err)
    if command == "frames":
        return _cmd_frames(args, project_dir, json_mode, env, out)
    if command in _STEP_COMMANDS:
        return _cmd_step(args, project_dir, json_mode, env, out, err)
    if command == "mcp":
        from . import mcp as mcp_module

        return mcp_module.serve(sys.stdin, out, err, env=env)
    raise ForjaError("USAGE", "comando desconhecido: %s" % command)


def main(argv=None, env=None, out=sys.stdout, err=sys.stderr):
    if env is None:
        env = os.environ
    # Plugins externos: uma vez por processo; falhas viram avisos em `providers`.
    registry.load_entry_points()
    workflows.load_entry_points()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    json_requested = "--json" in raw_argv
    _STREAMS["out"], _STREAMS["err"] = out, err

    try:
        # Importar os workflows registra os comandos/passos disponiveis.
        from .workflows import dub as _dub  # noqa: F401
        from .workflows import lote_digital as _lote_digital  # noqa: F401
        from .workflows import post as _post  # noqa: F401
        from .workflows import slides as _slides  # noqa: F401
        from .workflows import storyboard as _storyboard  # noqa: F401

        rest, json_mode, project_dir = _split_globals(raw_argv)
        if any(arg in ("-h", "--help") for arg in rest):
            parser = _build_parser()
            subs = next((a.choices for a in parser._actions if isinstance(a, argparse._SubParsersAction)), {})
            help_text = subs.get(rest[0], parser).format_help() if rest else parser.format_help()
            if json_mode:
                _write_json(out, _envelope({"help": help_text}))
            else:
                _stream_write(out, help_text)
            return 0
        args = _build_parser().parse_args(rest)
        return _dispatch(args, project_dir, json_mode, env, out, err)
    except _UsageError as exc:
        return _fail(ForjaError("USAGE", "uso invalido: %s" % _one_line(exc), hint="confira os argumentos com `forja --help`"), json_requested, out, err)
    except argparse.ArgumentError as exc:
        return _fail(ForjaError("USAGE", "uso invalido: %s" % _one_line(exc)), json_requested, out, err)
    except SystemExit as exc:
        if isinstance(exc.code, int) and exc.code == 0:
            return 0
        return _fail(ForjaError("USAGE", "uso invalido"), json_requested, out, err)
    except ForjaError as exc:
        return _fail(exc, json_requested, out, err)
    except config.ConfigError as exc:
        return _fail(ForjaError("CONFIG_INVALID", str(exc)), json_requested, out, err)
    except Exception as exc:  # nunca traceback para o usuario
        return _fail(ForjaError("INTERNAL", str(exc)), json_requested, out, err)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
