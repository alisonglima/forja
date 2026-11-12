"""Portoes humanos de revisao e aprovacao por hash do post/lote."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..errors import ForjaError

_REVIEW = "review"
_INSPECT = "inspect"
_DECISIONS = ("aprovado", "ajustes")
_CHUNK = 1024 * 1024


def _gate(msg, details=None) -> ForjaError:
    return ForjaError("GATE_FAILED", msg, details=details)


def _read_json(path, label) -> dict:
    if not path.is_file():
        raise _gate("%s ausente: %s" % (label, path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _gate("%s ilegivel: %s" % (label, path), {"error": str(exc)}) from exc
    if not isinstance(data, dict):
        raise _gate("%s deve ser um objeto" % label)
    return data


def _write_json(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def _safe_name(value) -> str:
    name = value if isinstance(value, str) else ""
    if (not name.strip() or name in (".", "..") or "/" in name
            or "\\" in name or "\x00" in name):
        raise _gate("peca invalida: %r" % (value,))
    return name


def _piece_from_review(ctx) -> str:
    review = Path(ctx.work) / _REVIEW
    names = sorted(path.stem for path in review.glob("*.json") if path.is_file())
    if len(names) != 1:
        raise _gate("esperava uma revisao em %s; achei %d" % (review, len(names)),
                    {"pieces": names})
    return _safe_name(names[0])


def _artifact(root, value) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise _gate("caminho de artefato invalido: %r" % (value,))
    if ".." in Path(value).parts:
        raise _gate("caminho de artefato escapa do projeto: %r" % (value,))
    path = Path(root) / value
    try:
        path.resolve().relative_to(Path(root).resolve())
    except (OSError, ValueError) as exc:
        raise _gate("caminho de artefato escapa do projeto: %r" % (value,)) from exc
    return path


def _sha256_file(path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as fh:
            while block := fh.read(_CHUNK):
                digest.update(block)
    except OSError as exc:
        raise ForjaError("APPROVAL_STALE", "artefato aprovado ilegivel: %s" % path,
                         details={"path": str(path), "error": str(exc)}) from exc
    return digest.hexdigest()


def _stale(msg, expected=None, current=None, piece=None, path=None) -> ForjaError:
    return ForjaError("APPROVAL_STALE", msg, details={
        "expected": expected, "current": current, "piece": piece, "path": path})


def run_review(ctx, piece=None) -> dict:
    """Confere inspect e capturas abertas, e registra a decisao humana."""
    piece = _safe_name(piece) if piece is not None else _piece_from_review(ctx)
    review = Path(ctx.work) / _REVIEW / ("%s.json" % piece)
    data = _read_json(review, "review")
    decision = data.get("decisao")
    if decision not in _DECISIONS:
        raise _gate("decisao de review invalida: %r" % (decision,),
                    {"piece": piece, "decisao": decision})
    _read_json(Path(ctx.work) / _INSPECT / ("%s.json" % piece), "inspect")
    for width in (1280, 360):
        marker = Path(ctx.work) / _REVIEW / ("%s.%d.aberta" % (piece, width))
        if not marker.is_file():
            raise _gate("captura de %d px nao aberta: %s" % (width, marker.name),
                        {"piece": piece, "marker": str(marker)})
    _write_json(review, data)
    return {"piece": piece, "decisao": decision, "notas": data.get("notas", "")}


def run_approve(ctx, piece=None) -> dict:
    """Valida a arte aprovada contra approvals.json e grava work/approve.json."""
    approvals = _read_json(Path(ctx.root) / "approvals.json", "approvals.json")
    if approvals.get("schema_version") != 2:
        raise _gate("aprovacao por hash exige schema_version 2")
    piece = _safe_name(piece) if piece is not None else _safe_name(approvals.get("piece"))
    hashed = approvals.get("hash")
    if not isinstance(hashed, dict):
        raise _gate("approvals.hash ausente", {"piece": piece})
    expected, label = hashed.get("valor"), hashed.get("arquivo")
    if not isinstance(expected, str) or not expected:
        raise _gate("approvals.hash.valor deve ser texto", {"piece": piece})
    if not isinstance(label, str) or not label:
        raise _gate("approvals.hash.arquivo deve ser texto", {"piece": piece})
    artifacts = approvals.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise _gate("approvals.artifacts deve listar a arte", {"piece": piece})
    checked = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise _gate("approvals.artifacts deve conter objetos", {"piece": piece})
        digest = artifact.get("sha256")
        if not isinstance(digest, str) or not digest:
            raise _gate("artefato sem sha256: %r" % (artifact.get("path"),))
        checked.append((_artifact(ctx.root, artifact.get("path")), digest))
    approved = _artifact(ctx.root, label)
    if not any(path == approved and digest == expected for path, digest in checked):
        raise _stale("aprovacao nao cobre a arte indicada", expected, None, piece, label)

    review = _read_json(Path(ctx.work) / _REVIEW / ("%s.json" % piece), "review")
    if review.get("decisao") != "aprovado":
        raise _gate("review ainda nao aprovou a peca: %r" % (review.get("decisao"),),
                    {"piece": piece, "decisao": review.get("decisao")})
    for path, digest in checked:
        if not path.is_file():
            raise _stale("artefato aprovado sumiu: %s" % path, digest, None, piece, str(path))
        current = _sha256_file(path)
        if current != digest:
            raise _stale("hash do artefato mudou", digest, current, piece, str(path))
    record = {"ok": True, "piece": piece, "artifacts": artifacts,
              "by": approvals.get("by", ""), "at": approvals.get("at", ""),
              "hash": {"algoritmo": "sha256", "valor": expected, "arquivo": label,
                       "bytes": hashed.get("bytes", approved.stat().st_size)}}
    _write_json(Path(ctx.work) / "approve.json", record)
    return record
