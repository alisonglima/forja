"""Passo `deliver` do workflow post: confere aprovacao e monta o pacote."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from ..errors import ForjaError

_CHUNK = 1024 * 1024
_ALGO = "sha256"

def _fail(code, msg, **details) -> ForjaError:
    return ForjaError(code, msg, details=details or None)

def _stale(msg, **details):
    raise _fail("APPROVAL_STALE", msg, **details)

def _read_json(path, label: str, missing: str = "MISSING_INPUT") -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        code = missing if isinstance(exc, OSError) else "CONFIG_INVALID"
        raise _fail(code, "%s ilegivel: %s" % (label, path)) from exc
    if not isinstance(data, dict):
        raise _fail("CONFIG_INVALID", "%s deve ser um objeto JSON" % label)
    return data

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(_CHUNK):
            digest.update(block)
    return digest.hexdigest()

def _artifact(root: Path, rel) -> Path:
    """Resolve o artefato aprovado dentro do projeto; ausente falha fechado."""
    if not isinstance(rel, str) or not rel.strip():
        raise _fail("ASSET_MISSING", "aprovacao sem artefato: %r" % (rel,))
    base = Path(root).resolve()
    target = (base / rel).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise _fail("ASSET_MISSING",
                    "artefato aprovado fora do projeto: %r" % rel)
    if not target.is_file():
        raise _fail("ASSET_MISSING", "artefato aprovado ausente: %s" % rel,
                    path=str(target))
    return target

def _approved(root: Path, approvals: dict):
    """Confere o hash aprovado contra o arquivo entregue; devolve (registro, arte, sha)."""
    record = approvals.get("hash")
    if not isinstance(record, dict):
        _stale("aprovacao sem hash do arquivo final")
    label = record.get("arquivo")
    target = _artifact(root, label)
    expected, actual = record.get("valor"), _sha256(target)
    if not isinstance(expected, str) or not expected:
        _stale("aprovacao com hash incompleto", path=str(target))
    if actual != expected:
        _stale("hash aprovado nao confere com %s" % label,
               expected=expected, current=actual, path=str(target),
               arquivo=label)
    if record.get("algoritmo") != _ALGO:
        _stale("algoritmo do hash aprovado deve ser sha256", path=str(target))
    return dict(record), target, actual

def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(path)

def _package(root: Path, piece: str, artifact: Path, record: dict,
             digest: str, cfg: dict) -> Path:
    """Monta `out/<peca>/` com a arte aprovada e os textos do copy/brief."""
    work = Path(root) / "work"
    copy = _read_json(work / "copy.json", "copy", missing="ASSET_MISSING")
    brief = _read_json(work / "brief.json", "brief", missing="ASSET_MISSING")
    legenda, alt, tags = copy.get("legenda"), copy.get("alt"), copy.get("hashtags")
    if not isinstance(legenda, str) or not isinstance(alt, str):
        raise _fail("ASSET_MISSING", "pacote sem legenda ou alt")
    if not isinstance(tags, list):
        raise _fail("ASSET_MISSING", "pacote sem hashtags", campo="hashtags")
    package = Path(root) / "out" / piece
    package.mkdir(parents=True, exist_ok=True)
    destination = package / artifact.name
    if destination.resolve() != artifact.resolve():
        shutil.copyfile(artifact, destination)
    textos = {
        "legenda.txt": legenda,
        "alt.txt": alt,
        "hashtags.txt": " ".join(
            t if str(t).startswith("#") else "#" + str(t) for t in tags),
    }
    for name, value in textos.items():
        (package / name).write_text(value, encoding="utf-8")
    horario = {}
    for source in (copy.get("horario"), brief.get("horario")):
        if isinstance(source, dict):
            horario = dict(source)
            break
    elementos = brief.get("elementos_ia")
    _write_json(package / "horario.json", horario)
    _write_json(package / "manifesto-ia.json",
                {"elementos_ia": elementos if isinstance(elementos, list) else []})
    files = ["legenda.txt", "hashtags.txt", "alt.txt", "horario.json",
             "manifesto-ia.json"]
    if destination.name not in files:
        files.append(destination.name)
    _write_json(package / "manifest.json", {
        "peca": piece,
        "brand_id": cfg.get("brand_id", ""),
        "format": cfg.get("format") or brief.get("format"),
        "aprovador": record.get("by"),
        "aprovado_em": record.get("at"),
        "hash": {"algoritmo": _ALGO, "valor": digest,
                 "arquivo": destination.relative_to(root).as_posix()},
        "arquivos": files,
        "hashes": {destination.name: digest},
    })
    return package

def run_deliver(ctx) -> dict:
    """Empacota a arte aprovada em `out/<peca>/` e grava `work/deliver.json`."""
    cfg = ctx.cfg or {}
    piece = cfg.get("piece")
    if not isinstance(piece, str) or not piece.strip():
        raise _fail("MISSING_INPUT", "config sem a peca do post")
    piece = piece.strip()
    root = Path(ctx.root)
    approvals = _read_json(root / "approvals.json", "approvals.json")
    record, artifact, digest = _approved(root, approvals)
    package = _package(root, piece, artifact, record, digest, cfg)
    payload = {
        "ok": True,
        "piece": piece,
        "artifact": artifact.relative_to(root).as_posix(),
        "sha256": digest,
        "package": package.relative_to(root).as_posix(),
        "arquivos": [path.name for path in sorted(package.iterdir())
                     if path.is_file()],
    }
    _write_json(Path(ctx.work) / "deliver.json", payload)
    return payload
