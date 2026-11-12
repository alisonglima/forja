"""Assets de `incoming/` para `work/assets.json` (L-ASSETS-01, plano:438,758).

Le so o manifesto canonico, valida arquivo/hash/licenca/origem/variante, copia
para `work/assets/` e grava o indice.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .errors import ForjaError

SCHEMA = "incoming/v1"
MANIFEST = "manifest.json"
ORIGENS = {"flow", "gemini", "ai-studio", "ai_studio", "manual"}
_SLUG = re.compile(r"[a-z0-9-]+\Z")
_CHUNK = 1024 * 1024


def _fail(code, msg, **details):
    raise ForjaError(code, msg, details=details or None)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _load_manifest(path: Path) -> list[dict]:
    if not path.is_file():
        _fail("ASSET_MISSING", "manifesto ausente: %s" % path, path=str(path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ForjaError("CONFIG_INVALID", "manifesto ilegivel: %s" % exc,
                         details={"path": str(path)}) from exc
    if not isinstance(data, dict):
        _fail("CONFIG_INVALID", "manifesto deve ser um objeto JSON", path=str(path))
    if data.get("schema") not in (None, SCHEMA):
        _fail("CONFIG_INVALID", "schema do manifesto deve ser %r" % SCHEMA,
              schema=data.get("schema"), path=str(path))
    items = data.get("items", data.get("assets"))
    if not isinstance(items, list):
        _fail("CONFIG_INVALID", "manifesto deve ter 'items' como lista", path=str(path))
    return items


def _source(root: Path, rel) -> Path:
    """Resolve `arquivo` relativo a raiz e exige que fique em `incoming/`."""
    if not isinstance(rel, str) or not rel.strip():
        _fail("ASSET_MISSING", "item sem 'arquivo'")
    path = Path(rel)
    try:
        candidate = (root / path).resolve()
        candidate.relative_to((root / "incoming").resolve())
    except (ValueError, OSError):
        _fail("CONFIG_INVALID", "caminho de ativo fora de incoming/: %r" % rel,
              arquivo=rel)
    if path.is_absolute() or ".." in path.parts or not candidate.is_file():
        _fail("ASSET_MISSING", "ativo ausente: %s" % rel, arquivo=rel)
    return candidate


def _slug(value) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail("CONFIG_INVALID", "variante deve ser texto nao vazio",
              variant=repr(value))
    variant = value.strip()
    if not _SLUG.fullmatch(variant):
        _fail("CONFIG_INVALID", "variante invalida: %r" % variant, variant=variant)
    return variant


def _known(variants) -> tuple[str, ...]:
    """Normaliza a lista fechada de variantes da marca."""
    if variants is None:
        return ()
    if not isinstance(variants, (list, tuple, set)):
        _fail("CONFIG_INVALID", "variantes da marca devem ser uma lista")
    return tuple(dict.fromkeys(_slug(value) for value in variants))


def _check(variant: str, known: tuple[str, ...]) -> str:
    if known and variant not in known:
        _fail("CONFIG_INVALID", "variante desconhecida: %s" % variant,
              variant=variant, variants=list(known))
    return variant


def _variant(item: dict, known: tuple[str, ...]) -> str | None:
    """Valida `variant` ou `variants[]`; exige escolha se a marca tem varias."""
    if "variant" in item:
        return _check(_slug(item["variant"]), known)
    listed = item.get("variants")
    if listed is not None:
        if not isinstance(listed, list) or not listed:
            _fail("CONFIG_INVALID", "variants deve ser lista nao vazia",
                  variants=repr(listed))
        for value in listed:
            _check(_slug(value), known)
        return listed[0] if len(listed) == 1 else None
    if len(known) > 1:
        _fail("BRAND_VARIANT_REQUIRED",
              "declare 'variant' no ativo; a marca tem mais de uma variante",
              variants=list(known))
    return known[0] if len(known) == 1 else None


def build_assets(root, variants=None) -> dict:
    """Valida o manifesto, copia os ativos e grava `work/assets.json`."""
    base = Path(root)
    known = _known(variants)
    entries: list[dict] = []
    seen: set[str] = set()
    for item in _load_manifest(base / "incoming" / MANIFEST):
        if not isinstance(item, dict):
            _fail("CONFIG_INVALID", "cada item do manifesto deve ser um objeto")
        rel = item.get("arquivo")
        source = _source(base, rel)
        license_ = item.get("license")
        if not isinstance(license_, str) or not license_.strip():
            _fail("CONFIG_INVALID", "ativo sem 'license': %s" % rel, arquivo=rel)
        origem = item.get("origem")
        if not isinstance(origem, str) or origem not in ORIGENS:
            _fail("CONFIG_INVALID", "origem desconhecida: %r" % origem,
                  arquivo=rel, origem=origem)
        chosen = _variant(item, known)
        digest = _sha256(source)
        if not isinstance(item.get("sha256"), str) or item["sha256"].lower() != digest:
            _fail("ASSET_HASH_MISMATCH", "sha256 de %s nao confere" % rel,
                  arquivo=rel, expected=item.get("sha256"), sha256=digest)
        size = source.stat().st_size
        declared = item.get("bytes")
        if declared is not None and (type(declared) is not int or declared != size):
            _fail("ASSET_HASH_MISMATCH", "bytes de %s nao confere" % rel,
                  arquivo=rel, declared=declared, bytes=size)
        name = Path(rel).name
        if not name or name in seen:
            _fail("CONFIG_INVALID", "nome de destino repetido: %s" % name, arquivo=rel)
        seen.add(name)
        dest = base / "work" / "assets" / name
        _write(dest, source.read_bytes())
        entry = dict(item)
        entry.update({
            "id": item.get("id") or Path(rel).stem,
            "sha256": digest,
            "bytes": size,
            "path": dest.relative_to(base).as_posix(),
        })
        if chosen and "variant" not in entry:
            entry["variant"] = chosen
        entries.append(entry)
    data = {"schema": "assets/v1", "assets": entries}
    _write(base / "work" / "assets.json",
             (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode())
    return data
