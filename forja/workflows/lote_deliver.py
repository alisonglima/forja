"""Empacota o lote-digital aprovado em ZIP com indice e manifesto.

Cada arte e conferida contra o sha256 de `approvals.json`; divergencia vira
APPROVAL_STALE e arte ausente vira ASSET_MISSING, sem rede ou relogio real.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from ..errors import ForjaError

_CHUNK = 1024 * 1024
_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
_INDEX = "indice.csv"
_MANIFEST = "manifest.json"
_RESERVED = (_INDEX, _MANIFEST)


def _fail(code, msg, **details):
    return ForjaError(code, msg, details=details or None)


def _read(path):
    """Le `approvals.json`; ausente, ilegivel ou vazio e APPROVAL_STALE."""
    path = Path(path)
    if not path.is_file():
        raise _fail("APPROVAL_STALE", "approvals.json ausente: %s" % path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _fail("APPROVAL_STALE", "approvals.json ilegivel: %s" % exc) from exc
    artifacts = data.get("artifacts") if isinstance(data, dict) else None
    if not isinstance(artifacts, list) or not artifacts:
        raise _fail("APPROVAL_STALE", "approvals.artifacts ausente ou vazio")
    return data


def _safe(root, rel):
    """Resolve `rel` dentro de `root`; devolve (arquivo, rotulo normalizado)."""
    if not isinstance(rel, str) or not rel.strip():
        raise _fail("CONFIG_INVALID", "artefato sem caminho relativo")
    raw = Path(rel)
    if raw.is_absolute():
        raise _fail("CONFIG_INVALID", "artefato nao pode ser absoluto: %r" % rel)
    base = Path(root).resolve()
    target = (base / raw).resolve()
    try:
        return target, target.relative_to(base).as_posix()
    except ValueError as exc:
        raise _fail("CONFIG_INVALID", "artefato escapa do lote: %r" % rel) from exc


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(_CHUNK):
            digest.update(block)
    return digest.hexdigest()


def _artifacts(root, approvals):
    """Valida cada arte aprovada e devolve as linhas do indice ordenadas."""
    rows, seen = [], set()
    for artifact in approvals["artifacts"]:
        if not isinstance(artifact, dict):
            raise _fail("APPROVAL_STALE", "aprovacao com artifact invalido")
        expected = artifact.get("sha256")
        if not isinstance(expected, str) or not expected:
            raise _fail("APPROVAL_STALE", "artefato aprovado sem sha256: %r"
                        % (artifact.get("path"),))
        target, label = _safe(root, artifact.get("path"))
        if label in seen or label in _RESERVED:
            raise _fail("CONFIG_INVALID", "artefato invalido na aprovacao: %s" % label)
        seen.add(label)
        if not target.is_file():
            raise _fail("ASSET_MISSING", "arte aprovada ausente: %s" % label,
                        path=label)
        actual = _sha256(target)
        if actual != expected:
            raise ForjaError(
                "APPROVAL_STALE", "hash aprovado nao confere com %s" % label,
                details={"path": label, "expected": expected, "current": actual})
        rows.append({"path": label, "sha256": actual,
                     "bytes": target.stat().st_size})
    return sorted(rows, key=lambda row: row["path"])


def _csv_bytes(rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["path", "sha256", "bytes"],
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _write_zip(destino, root, rows, approvals, agora):
    """Escreve o ZIP de forma atomica e devolve o manifesto empacotado."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporary = destino.with_name(destino.name + ".part")
    record = approvals.get("hash")
    manifest = {"schema_version": 1, "gerado_em": agora or "",
                "aprovador": approvals.get("by"),
                "aprovado_em": approvals.get("at"), "total": len(rows),
                "artefatos": rows, "hash": record if isinstance(record, dict) else {}}
    entries = [(row["path"], (Path(root) / row["path"]).read_bytes())
               for row in rows]
    entries.append((_INDEX, _csv_bytes(rows)))
    entries.append((_MANIFEST, (json.dumps(
        manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")))
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, payload in entries:
                info = zipfile.ZipInfo(name, date_time=_ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, payload)
        temporary.replace(destino)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return manifest


def run_deliver_lote(renders, aprovacoes, destino, *, agora=None) -> dict:
    """Empacota as artes aprovadas e devolve total, caminho, indice e manifesto."""
    approvals = _read(aprovacoes)
    rows = _artifacts(renders, approvals)
    manifest = _write_zip(destino, renders, rows, approvals, agora)
    return {"total": len(rows), "zip": str(destino), "indice": rows,
            "manifest": manifest}
