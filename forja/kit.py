"""Wrapper do kit de design (`@feimacode/open-design-agent-kit`).

Monta argv pinado, sem shell, e roda `check`/`export` em modo LOCAL com
`run=` injetavel. A saida pode vir precedida de banner do npx; o ultimo
objeto JSON e o contrato.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from forja.errors import ForjaError

_KIT = "@feimacode/open-design-agent-kit"
_SLUG = re.compile(r"[a-z0-9-]+\Z")
_MISSING = ("404", "not found", "no matching version",
            "could not determine executable")


def _fail(code, msg, **details) -> ForjaError:
    return ForjaError(code, msg, details=details or None)


def _text(value) -> str:
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else (value or "")


def _last_json(text) -> dict | None:
    """Ultimo objeto JSON da saida, ignorando banners antes/depois."""
    raw = _text(text)
    decoder = json.JSONDecoder()
    found, found_end = None, -1
    for index, char in enumerate(raw):
        if char != "{":
            continue
        try:
            value, end = decoder.raw_decode(raw[index:])
        except ValueError:
            continue
        if isinstance(value, dict) and end > found_end:
            found, found_end = value, end
    return found


def _variants_path(cwd) -> Path | None:
    root = Path(__file__).resolve().parent.parent
    for base in dict.fromkeys((Path(cwd) if cwd else Path.cwd(), root)):
        if (base / "variants.json").is_file():
            return base / "variants.json"
        found = sorted((base / "brands").glob("*/variants.json"))
        if found:
            return found[0]
    return None


def _known_variants(cwd) -> set | None:
    if (path := _variants_path(cwd)) is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _fail("CONFIG_INVALID", f"variants.json invalido: {path}",
                    path=str(path)) from exc
    variants = data.get("variants") if isinstance(data, dict) else None
    if not isinstance(variants, dict):
        raise _fail("CONFIG_INVALID", f"variants.json sem 'variants': {path}", path=str(path))
    return set(variants)


def _variant(value, cwd) -> str | None:
    """Valida o slug e a lista fechada declarada em variants.json."""
    if value is None: return None
    if not isinstance(value, str) or not value.strip():
        raise _fail("CONFIG_INVALID", "variante deve ser texto nao vazio")
    variant = value.strip()
    if not _SLUG.fullmatch(variant):
        raise _fail("CONFIG_INVALID", f"variante invalida: {variant!r}",
                    variant=variant)
    known = _known_variants(cwd)
    if known is not None and variant not in known:
        raise _fail("CONFIG_INVALID", f"variante desconhecida: {variant}",
                    variant=variant, variants=sorted(known))
    return variant


def _cmd(action, target, variant, npx, version) -> list[str]:
    command = [str(npx), "--yes", f"{_KIT}@{version}", action, str(target)]
    if action == "check":
        command += ["--fail-on", "error", "--json"]
    if variant:
        command += ["--variant", variant]
    return command


def _invoke(command, run, what) -> subprocess.CompletedProcess:
    try:
        return run(command, capture_output=True, text=True, shell=False)
    except FileNotFoundError as exc:
        raise _fail("MISSING_PREREQ",
                    f"{command[0]} nao encontrado; instale Node.js/npm",
                    cmd=command[0], what=what) from exc


def _failure(proc, what: str) -> ForjaError:
    stderr = _text(proc.stderr)
    code = ("MISSING_PREREQ" if any(m in stderr.lower() for m in _MISSING)
            else "PROVIDER_ERROR")
    return _fail(code, f"{what} falhou (exit {proc.returncode})", cmd=what,
                 returncode=proc.returncode, stderr_tail=stderr[-500:])


def check_issues(payload) -> list[dict]:
    """Converte `errors` do kit em issues com level/code/msg."""
    errors = payload.get("errors") if isinstance(payload, dict) else None
    if not isinstance(errors, list):
        return []
    return [{"level": e.get("level") or "error",
             "code": e.get("rule") or e.get("code") or "KIT",
             "file": e.get("file"), "line": e.get("line"),
             "msg": str(e.get("message") or e.get("msg") or "")}
            for e in errors if isinstance(e, dict)]


def check(target, *, variant=None, run=subprocess.run, npx="npx",
          version="0.4.0", cwd=None) -> dict:
    """Roda o preflight do kit e devolve `{"ok", "issues", "payload"}`."""
    variant = _variant(variant, cwd)
    command = _cmd("check", target, variant, npx, version)
    proc = _invoke(command, run, "kit check")
    payload = _last_json(proc.stdout)
    if payload is None:
        if proc.returncode:
            raise _failure(proc, "kit check")
        raise _fail("PROVIDER_ERROR", "kit check nao devolveu JSON",
                    cmd=command[0], returncode=proc.returncode,
                    stdout_tail=_text(proc.stdout)[-500:])
    issues = check_issues(payload)
    return {"ok": not issues, "issues": issues, "payload": payload}


def require_check(target, *, variant=None, run=subprocess.run, npx="npx",
                  version="0.4.0", cwd=None) -> dict:
    """Como `check`, mas reprova com `GATE_FAILED` quando ha issue."""
    result = check(target, variant=variant, run=run, npx=npx,
                   version=version, cwd=cwd)
    if result["issues"]:
        raise _fail("GATE_FAILED",
                    f"kit check reprovou com {len(result['issues'])} issue(s)",
                    issues=result["issues"])
    return result


def export(target, *, variant=None, run=subprocess.run, npx="npx",
           version="0.4.0", cwd=None) -> dict:
    """Roda `export` do kit e devolve `{"ok", "outputs", "cmd"}`."""
    variant = _variant(variant, cwd)
    command = _cmd("export", target, variant, npx, version)
    proc = _invoke(command, run, "kit export")
    if proc.returncode:
        raise _failure(proc, "kit export")
    payload = _last_json(proc.stdout)
    if payload is not None:
        outputs = [str(item) for item in
                   (payload.get("files") or payload.get("outputs") or [])]
    else:
        outputs = [line.strip() for line in _text(proc.stdout).splitlines()
                   if line.strip()]
    return {"ok": True, "outputs": outputs, "payload": payload, "cmd": command}
