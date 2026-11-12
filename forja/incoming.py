"""Ingestao canonica de `incoming/` e sidecars `*.meta.json` (N-27, plano 758-782)."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from .errors import ForjaError

SCHEMA = "incoming/v1"
MANIFEST = "manifest.json"
SIDECAR_SUFFIX = ".meta.json"
# Campos que o plano:758 exige em todo sidecar; sha256 fecha o hash declarado.
_REQUIRED = ("origem", "conta", "ferramenta", "data", "sha256")


def _issue(code: str, msg: str, path=None) -> dict:
    issue = {"level": "error", "code": code, "msg": msg}
    if path is not None:
        issue["path"] = str(path)
    return issue


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(base: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
    except ValueError:
        return False
    return True


def _load_sidecar(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ForjaError(
            "CONFIG_INVALID",
            "sidecar ilegivel em %s: %s" % (path, exc),
            hint="o sidecar deve ser um objeto JSON valido",
        ) from exc
    if not isinstance(data, dict):
        raise ForjaError(
            "CONFIG_INVALID",
            "sidecar deve ser um objeto JSON em %s" % path,
            hint="corrija o *.meta.json para um mapeamento de chaves",
        )
    if data.get("origem") == "manual" and not data.get("license"):
        raise ForjaError(
            "MISSING_INPUT",
            "origem manual exige license no sidecar %s" % path,
            hint="informe a licenca de uso do ativo manual antes de ingerir",
        )
    return data


def _missing(meta: dict) -> list[str]:
    missing = [key for key in _REQUIRED if meta.get(key) in (None, "")]
    if meta.get("origem") == "manual" and not meta.get("license"):
        missing.append("license")
    return missing


def scan_incoming(root) -> list[dict]:
    """Varre `incoming/` e devolve issues (level/code/msg) sem gravar nada."""
    base = Path(root) / "incoming"
    if not base.is_dir():
        return []
    issues: list[dict] = []
    for asset in sorted(base.iterdir()):
        if not asset.is_file() or asset.name == MANIFEST or asset.name.endswith(SIDECAR_SUFFIX):
            continue
        sidecar = asset.with_name(asset.name + SIDECAR_SUFFIX)
        if not sidecar.is_file():
            issues.append(_issue(
                "INCOMING_INCOMPLETE",
                "ativo %s sem sidecar %s" % (asset.name, sidecar.name),
                asset,
            ))
            continue
        try:
            meta = _load_sidecar(sidecar)
        except ForjaError as exc:
            issues.append(_issue(exc.code, exc.msg, sidecar))
            continue
        missing = _missing(meta)
        if missing:
            issues.append(_issue(
                "INCOMING_INCOMPLETE",
                "sidecar %s sem: %s" % (sidecar.name, ", ".join(missing)),
                sidecar,
            ))
        elif meta["sha256"] != _sha256(asset):
            issues.append(_issue(
                "ASSET_HASH_MISMATCH",
                "sha256 de %s nao confere com o sidecar" % asset.name,
                asset,
            ))
    return issues


def _load_manifest(path: Path) -> dict:
    if not path.is_file():
        return {"schema": SCHEMA, "items": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ForjaError("CONFIG_INVALID", "manifesto ilegivel: %s" % exc) from exc
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ForjaError("CONFIG_INVALID", "manifesto deve ter schema e items")
    return data


def _write_manifest(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".manifest.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def ingest(root, asset, sidecar) -> dict:
    """Registra um ativo no manifesto canonico; nunca reescreve os bytes."""
    base = (Path(root) / "incoming").resolve()
    asset = Path(asset)
    sidecar = Path(sidecar) if sidecar is not None else asset.with_name(asset.name + SIDECAR_SUFFIX)
    if not _inside(base, asset):
        raise ForjaError(
            "CONFIG_INVALID",
            "ativo fora de incoming/: %s" % asset,
            hint="mova o ativo para incoming/ antes de ingerir",
        )
    if not _inside(base, sidecar):
        raise ForjaError(
            "CONFIG_INVALID",
            "sidecar fora de incoming/: %s" % sidecar,
            hint="o sidecar deve ficar ao lado do ativo em incoming/",
        )
    if not asset.is_file():
        raise ForjaError("MISSING_INPUT", "ativo ausente: %s" % asset)
    meta = _load_sidecar(sidecar) if sidecar.is_file() else {}
    missing = _missing(meta)
    if missing:
        raise ForjaError(
            "INCOMING_INCOMPLETE",
            "metadados ausentes para %s: %s" % (asset.name, ", ".join(missing)),
            hint="preencha origem, conta, ferramenta, data e sha256 no sidecar",
        )
    digest = _sha256(asset)
    if meta["sha256"] != digest:
        raise ForjaError(
            "ASSET_HASH_MISMATCH",
            "sha256 de %s nao confere com o sidecar" % asset.name,
            hint="recalcule o sha256 do arquivo e atualize o sidecar",
        )
    item = dict(meta)
    item.update({
        "id": item.get("id") or asset.stem,
        "arquivo": asset.resolve().relative_to(Path(root).resolve()).as_posix(),
        "sha256": digest,
        "bytes": asset.stat().st_size,
    })
    manifest_path = base / MANIFEST
    manifest = _load_manifest(manifest_path)
    manifest["schema"] = SCHEMA
    manifest["items"] = [
        old for old in manifest["items"]
        if not (isinstance(old, dict) and old.get("arquivo") == item["arquivo"])
    ] + [item]
    _write_manifest(manifest_path, manifest)
    return item
