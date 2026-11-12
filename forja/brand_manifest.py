"""Manifest de marca: carrega, valida e hasheia (plano:730,767,1967-1997).

Em `provisorio`, arquivo declarado ausente e pendencia; em `final`, e erro. O
cross-check confere lista/default, paleta sem hex duplicado e paletas por
variante; chaves de fonte, licenca, logo, voz e aprovador nao sao inventadas.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from forja.errors import ForjaError

_HEX = re.compile(r"#[0-9A-Fa-f]{6}\Z")
_COVERED = ("manifest.json", "variants.json", "voice.json")
_REQUIRED = ("schema", "brand_id", "status", "variants", "default_variant", "variants_file", "palette")

def _issue(level, code, msg, **details):
    return {"level": level, "code": code, "msg": msg, **details}

def _error(code, msg, **details):
    return _issue("error", code, msg, **details)

def _pending(msg, **details):
    return _issue("warning", "BRAND_FILE_MISSING", msg, **details)

def _hex(value):
    return isinstance(value, str) and _HEX.fullmatch(value.strip()) is not None

def _relative(value):
    """So nome/caminho relativo contido na raiz (sem '..' nem absoluto)."""
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip()
    path = PurePosixPath(text.replace("\\", "/"))
    return (not text.startswith(("/", "\\", "~")) and not path.is_absolute()
            and ".." not in path.parts and not path.parts[0].endswith(":"))

def _read_object(path):
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, str(exc)
    return (doc, None) if isinstance(doc, dict) else (None, "raiz do JSON nao e objeto")

def load_manifest(path) -> dict:
    """Le `manifest.json` e devolve o objeto JSON; falha fechada se invalido."""
    manifest = Path(path)
    if not manifest.is_file():
        raise ForjaError("MISSING_INPUT", f"manifest nao encontrado: {manifest}",
                         details={"path": str(manifest)})
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ForjaError("CONFIG_INVALID", f"manifest invalido: {manifest}",
                         details={"path": str(manifest)}) from exc
    if not isinstance(data, dict):
        raise ForjaError("CONFIG_INVALID", f"manifest deve ser objeto JSON: {manifest}", details={"path": str(manifest)})
    return data

def _palette_issues(palette):
    if not isinstance(palette, list) or not palette:
        return [_error("BRAND_PALETTE_INVALID", "palette deve ser lista nao vazia de hex #RRGGBB")]
    issues, seen = [], set()
    for item in palette:
        if not _hex(item):
            issues.append(_error("BRAND_PALETTE_INVALID", f"cor invalida na palette: {item!r}",
                                 palette=repr(item)))
            continue
        color = item.strip().lower()
        if color in seen:
            issues.append(_error("BRAND_PALETTE_DUPLICATE", f"hex duplicado na palette: {color}",
                                 hex=color))
        seen.add(color)
    return issues

def _declared_variants(data):
    """Devolve (nomes, issues) de `data['variants']`, sem inventar ids."""
    value = data.get("variants")
    if not isinstance(value, list) or not value:
        return None, [_error("BRAND_VARIANTS_INVALID", "variants deve ser lista nao vazia de ids")]
    issues, seen, names = [], set(), []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            issues.append(_error("BRAND_VARIANTS_INVALID", f"variante invalida: {item!r}",
                                 variant=repr(item)))
            continue
        name = item.strip()
        if name in seen:
            issues.append(_error("BRAND_VARIANTS_INVALID", f"variante repetida: {name}",
                                 variant=name))
        seen.add(name)
        names.append(name)
    return names, issues

def _variant_issues(entry, name):
    if not isinstance(entry, dict):
        return [_error("BRAND_VARIANT_INVALID", f"variante deve ser objeto: {name}", variant=name)]
    issues = []
    palette = entry.get("paleta")
    if not isinstance(palette, dict) or not palette:
        issues.append(_error("BRAND_VARIANT_INVALID", f"variante sem 'paleta' nao vazia: {name}",
                             variant=name))
    else:
        for role, color in sorted(palette.items()):
            if not _hex(color):
                issues.append(_error("BRAND_VARIANT_INVALID",
                                     f"cor invalida em {name}.{role}: {color!r}",
                                     variant=name, role=role))
    accent = entry.get("accent")
    if accent is not None and not _hex(accent):
        issues.append(_error("BRAND_VARIANT_INVALID", f"accent invalido em {name}: {accent!r}",
                             variant=name))
    return issues

def _variants_doc_issues(doc, declared, default):
    """Cross-check de `variants.json`: lista/default e paleta por variante."""
    if not isinstance(doc, dict):
        return [_error("BRAND_VARIANTS_INVALID", "variants_file deve conter um objeto JSON")]
    entries = doc.get("variants")
    if not isinstance(entries, dict) or not entries:
        return [_error("BRAND_VARIANTS_INVALID", "variants_file deve ter 'variants' como objeto nao vazio")]
    issues = []
    if declared is not None:
        missing = sorted(set(declared) - set(entries))
        extra = sorted(set(entries) - set(declared))
        if missing or extra:
            issues.append(_error("BRAND_VARIANT_LIST_MISMATCH",
                                 "variants do manifest difere das chaves de variants_file",
                                 missing=missing, extra=extra))
    if isinstance(default, str) and default.strip() and default.strip() not in entries:
        issues.append(_error("BRAND_DEFAULT_VARIANT_INVALID",
                             f"default_variant ausente em variants_file: {default}",
                             default_variant=default))
    for name in sorted(entries):
        issues.extend(_variant_issues(entries[name], name))
    return issues

def _file_issues(root, value, label, provisional, issues):
    """Confere caminho declarado e existencia; devolve o objeto se carregar."""
    if not _relative(value):
        issues.append(_error("BRAND_PATH_UNSAFE", f"{label} deve ser relativo, sem '..': {value!r}",
                             path=repr(value)))
        return None, False
    path = Path(root) / value.strip()
    if not path.is_file():
        msg = f"{label} declarado mas ausente: {value}"
        if provisional:
            issues.append(_pending(msg, path=str(path), file=label))
        else:
            issues.append(_error("BRAND_FILE_MISSING", msg, path=str(path), file=label))
        return None, False
    doc, err = _read_object(path)
    if err is not None:
        issues.append(_error("BRAND_FILE_INVALID", f"{label} invalido: {value}: {err}",
                             path=str(path), file=label))
        return None, False
    return doc, True

def validate_manifest(data, root, variants=None) -> list[dict]:
    """Valida o manifest de marca; devolve issues com `level`/`code`/`msg`."""
    if not isinstance(data, dict):
        return [_error("BRAND_MANIFEST_INVALID", "manifest deve ser um objeto JSON")]
    issues = [_error("BRAND_MANIFEST_INVALID", f"chave obrigatoria ausente: {key}", key=key)
              for key in _REQUIRED if key not in data]
    issues += [_error("BRAND_MANIFEST_INVALID", f"{key} deve ser texto nao vazio", key=key)
               for key in ("schema", "brand_id")
               if key in data and (not isinstance(data[key], str) or not data[key].strip())]
    status = data.get("status")
    if "status" in data and status not in ("provisorio", "final"):
        issues.append(_error("BRAND_STATUS_INVALID", f"status invalido: {status!r}; "
                             "use 'provisorio' ou 'final'", status=repr(status)))
    provisional = status == "provisorio"
    declared, declared_issues = _declared_variants(data)
    issues.extend(declared_issues)
    default = data.get("default_variant")
    if declared is not None:
        if not isinstance(default, str) or not default.strip():
            issues.append(_error("BRAND_DEFAULT_VARIANT_INVALID",
                                 "default_variant deve ser texto nao vazio"))
        elif default.strip() not in declared:
            issues.append(_error("BRAND_DEFAULT_VARIANT_INVALID",
                                 f"default_variant fora de variants: {default}",
                                 default_variant=default))
    if "palette" in data:
        issues.extend(_palette_issues(data["palette"]))

    variants_doc = None
    if "variants_file" in data:
        if variants is not None:
            variants_doc = variants if isinstance(variants, dict) else None
            if variants_doc is None:
                issues.append(_error("BRAND_VARIANTS_INVALID",
                                     "variants pre-carregado deve ser objeto JSON"))
        else:
            variants_doc, _ = _file_issues(
                root, data["variants_file"], "variants_file", provisional, issues)
        if variants_doc is not None:
            issues.extend(_variants_doc_issues(variants_doc, declared, default))

    if data.get("voice_file") is not None:
        _file_issues(root, data["voice_file"], "voice_file", provisional, issues)
    return issues

def brand_hash(root) -> str:
    """sha256 dos arquivos de marca presentes, na ordem fixa do contrato."""
    base = Path(root)
    if not (base / "manifest.json").is_file():
        raise ForjaError("MISSING_INPUT", f"manifest.json nao encontrado em: {base}",
                         details={"root": str(base)})
    digest = hashlib.sha256()
    for name in _COVERED:
        path = base / name
        if path.is_file():
            digest.update(name.encode("utf-8") + b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()
