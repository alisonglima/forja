"""Amostra deterministica do lote-digital: contraste, dedup e QR.

Seleciona a primeira peca, o nome mais longo, a de mais acentos, as
multilinha e o QR mais denso; mede o contraste sob o texto, compara o
sha256 com os hashes ja vistos e grava `work/lote/sample.json`.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from ..dedup import content_hash
from ..errors import ForjaError

_CONTRAST = 4.5
_QR_MAX = 2000
_EXTS = (".png", ".jpg", ".jpeg", ".pdf")


def _fail(code, msg, **details):
    return ForjaError(code, msg, details=details or None)


def _read_plan(path):
    """Le o plano JSON do lote; ausente, vazio ou ilegivel vira MISSING_INPUT."""
    path = Path(path)
    if not path.is_file():
        raise _fail("MISSING_INPUT", "plano do lote nao encontrado: %s" % path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _fail("MISSING_INPUT", "plano do lote ilegivel: %s" % path) from exc
    if not isinstance(data, list) or not data:
        raise _fail("MISSING_INPUT", "plano do lote vazio ou invalido")
    for entry in data:
        if not isinstance(entry, dict):
            raise _fail("MISSING_INPUT", "plano do lote com item invalido")
    return data


def _acentos(text) -> int:
    """Conta caracteres com diacritico no texto (acentos preservados)."""
    normalized = unicodedata.normalize("NFD", str(text or ""))
    return sum(1 for char in normalized if unicodedata.combining(char))


def _pick(entries) -> list[int]:
    """Indices da amostra: primeira, nome longo, acentos, multilinha, QR denso."""
    def best(key):
        return max(range(len(entries)), key=lambda i: key(entries[i]))

    picked = {0}
    picked.add(best(lambda p: len(str(p.get("nome") or ""))))
    picked.add(best(lambda p: _acentos(str(p.get("nome") or "")) + _acentos(p.get("texto"))))
    for index, piece in enumerate(entries):
        if "\n" in str(piece.get("texto") or ""):
            picked.add(index)
    picked.add(best(lambda p: len(str(p.get("qr") or ""))))
    return sorted(picked)


def _slug(piece) -> str:
    slug = str(piece.get("slug") or "").strip()
    if not slug or Path(slug).name != slug:
        raise _fail("GATE_FAILED", "slug invalido na amostra: %r" % slug)
    return slug


def _render(renders, slug) -> Path:
    """Acha o render da peca pela extensao; ausente reprova o gate."""
    for ext in _EXTS:
        path = Path(renders) / (slug + ext)
        if path.is_file():
            return path
    raise _fail("GATE_FAILED", "render da amostra ausente: %s" % slug)


def _hashes(vistos) -> set:
    result = set()
    for item in vistos or ():
        value = item.get("hash") if isinstance(item, dict) else item
        if value:
            result.add(str(value).lower())
    return result


def _ratio(value) -> float:
    if isinstance(value, dict):
        value = value.get("ratio", value.get("min"))
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise _fail("GATE_FAILED", "contraste invalido na amostra") from exc


def _write_json(path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_sample_check(plano, renders, saida, *, contraste=None,
                     vistos=frozenset()) -> dict:
    """Confere a amostra deterministica e grava `sample.json`.

    `contraste` recebe o caminho do render e devolve a razao medida;
    `vistos` traz os sha256 ja registrados. Falha em QR acima de 2000,
    contraste abaixo de 4.5:1, arte duplicada ou render ausente.
    """
    entries = _read_plan(plano)
    picked = _pick(entries)
    known = _hashes(vistos)
    hashes = {}
    for index in picked:
        piece = entries[index]
        slug = _slug(piece)
        qr = str(piece.get("qr") or "")
        if len(qr) > _QR_MAX:
            raise _fail(
                "GATE_FAILED",
                "payload de QR com %d caracteres (limite %d) em %s"
                % (len(qr), _QR_MAX, slug),
                slug=slug, limite=_QR_MAX)
        path = _render(renders, slug)
        digest = content_hash(path)
        if digest.lower() in known:
            raise ForjaError(
                "DUPLICATE_ARTIFACT",
                "arte da amostra ja existe com este sha256: %s" % slug,
                details={"slug": slug, "sha256": digest})
        if contraste is not None:
            ratio = _ratio(contraste(path))
            if ratio + 1e-9 < _CONTRAST:
                raise ForjaError(
                    "CONTRAST_PHOTO",
                    "contraste %.2f:1 abaixo de %.1f:1 na amostra %s"
                    % (ratio, _CONTRAST, slug),
                    details={"slug": slug, "ratio": ratio})
        hashes[slug] = digest
    result = {
        "total": len(entries),
        "amostra": [_slug(entries[i]) for i in picked],
        "hashes": hashes,
    }
    _write_json(saida, result)
    return result
