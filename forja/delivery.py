"""Monta `entrega/` para o Meta Business Suite (N-26; plano:754).

O pacote leva arte, legenda, hashtags, alt, horario, manifesto de IA e
manifesto de hashes. Quem agenda/publica e o humano no Business Suite; o
modulo so empacota e recusa aprovacao vencida, formato fora da matriz,
limites de texto estourados e elemento de IA sem rotulo.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from . import grafia
from .errors import ForjaError

_CHUNK = 1024 * 1024
_HASH_ALGO = "sha256"


def _fail(code, msg, **details):
    raise ForjaError(code, msg, details=details or None)


def _stale(msg):
    _fail("APPROVAL_STALE", msg,
          hint="revise a peca e rode `forja approve` de novo com o hash atual")


def _text(value, key, code="BRIEF_INCOMPLETE"):
    if not isinstance(value, str) or not value.strip():
        _fail(code, "brief.%s deve ser texto nao vazio" % key)
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(_CHUNK):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path, label: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _fail("CONFIG_INVALID", "%s ilegivel: %s" % (label, exc))
    if not isinstance(data, dict) or not data:
        _fail("CONFIG_INVALID", "%s deve ser um objeto nao vazio" % label)
    return data


def _row(formats, ident: str) -> dict:
    if not isinstance(formats, dict):
        _fail("CONFIG_INVALID", "matriz de formatos deve ser um objeto")
    rows = formats.get("formatos")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("id") == ident:
                return row
    else:
        row = formats.get(ident)
        if isinstance(row, dict):
            return row
    _fail("FORMAT_UNSUPPORTED", "formato fora da matriz: %r" % ident)


def _limit(row, key: str, default: int) -> int:
    value = row.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _fail("CONFIG_INVALID", "formato.%s deve ser inteiro nao negativo" % key)
    return value


def _safe_file(root: Path, rel) -> Path:
    """Resolve `rel` dentro de `root`; recusa absoluto, traversal e ausente."""
    if not isinstance(rel, str) or not rel.strip():
        _fail("BRIEF_INCOMPLETE", "brief.arte deve ser caminho relativo")
    raw = Path(rel)
    if raw.is_absolute():
        _fail("CONFIG_INVALID", "brief.arte nao pode ser absoluto: %r" % rel)
    base = Path(root).resolve()
    target = (base / raw).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        _fail("CONFIG_INVALID", "brief.arte escapa do projeto: %r" % rel)
    if not target.is_file():
        _fail("MISSING_INPUT", "arte ausente: %s" % rel)
    return target


def _approved(root: Path, approvals, arte: str) -> tuple[dict, str]:
    """Confere o hash aprovado contra o arquivo entregue; devolve (hash, sha)."""
    if not isinstance(approvals, dict) or not approvals:
        _stale("aprovacao ausente: rode `forja approve` antes de entregar")
    record = approvals.get("hash")
    if not isinstance(record, dict):
        _stale("aprovacao sem hash do arquivo final")
    if record.get("algoritmo") != _HASH_ALGO:
        _stale("algoritmo do hash aprovado deve ser sha256")
    value = record.get("valor")
    arquivo = record.get("arquivo")
    if not isinstance(value, str) or not isinstance(arquivo, str) or not arquivo:
        _stale("aprovacao com hash incompleto")
    target = _safe_file(root, arquivo)
    actual = _sha256(target)
    if actual != value:
        _stale("hash aprovado nao confere com %s" % arquivo)
    if Path(arquivo) != Path(arte):
        _stale("hash aprovado aponta para %s, nao para %s" % (arquivo, arte))
    artifacts = approvals.get("artifacts")
    if artifacts is not None:
        if not isinstance(artifacts, list):
            _stale("aprovacao com artifacts invalidos")
        matched = [a for a in artifacts if isinstance(a, dict)
                   and a.get("path") == arquivo]
        if not matched or matched[0].get("sha256") != actual:
            _stale("artifacts nao conferem com o hash aprovado")
    return dict(record), actual


def _elements(brief: dict, now) -> dict:
    elements = brief.get("elementos_ia")
    if elements is None:
        elements = []
    if not isinstance(elements, list):
        _fail("BRIEF_INCOMPLETE", "brief.elementos_ia deve ser lista")
    out = []
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            _fail("BRIEF_INCOMPLETE", "elemento IA #%d deve ser objeto" % index)
        rotulo = element.get("rotulo")
        if not isinstance(rotulo, dict) or "exigido" not in rotulo:
            _fail("BRIEF_INCOMPLETE",
                  "elemento IA #%d sem rotulo (rotulo.exigido obrigatorio)" % index)
        out.append(dict(element))
    return {
        "piece": brief.get("piece"),
        "brand_id": brief.get("brand_id"),
        "format": brief.get("format"),
        "gerado_em": now or "",
        "elementos_ia": out,
    }


def build_package(root, *, brief, brand_root, formats, approvals, now=None) -> dict:
    """Cria `entrega/` e devolve o manifesto de hashes do pacote."""
    if not isinstance(brief, dict) or not brief:
        _fail("BRIEF_INCOMPLETE", "brief vazio: nada para entregar")
    root = Path(root)
    piece = _text(brief.get("piece"), "piece")
    brand_id = _text(brief.get("brand_id"), "brand_id")
    ident = _text(brief.get("format"), "format")
    legenda = _text(brief.get("legenda"), "legenda")
    alt = brief.get("alt")
    if not isinstance(alt, str):
        _fail("BRIEF_INCOMPLETE", "brief.alt deve ser texto")
    arte = _text(brief.get("arte"), "arte")
    horario = brief.get("horario")
    if not isinstance(horario, dict):
        _fail("BRIEF_INCOMPLETE", "brief.horario deve ser objeto")
    sugestao = _text(horario.get("sugestao"), "horario.sugestao")
    fuso = _text(horario.get("fuso"), "horario.fuso")

    hashtags = brief.get("hashtags")
    if not isinstance(hashtags, list) or any(
            not isinstance(tag, str) or not tag.strip() for tag in hashtags):
        _fail("BRIEF_INCOMPLETE", "brief.hashtags deve ser lista de textos")

    row = _row(formats, ident)
    alt_max = _limit(row, "alt_max", 100)
    hashtag_max = _limit(row, "max_hashtags", 30)
    if len(alt) > alt_max:
        _fail("BRIEF_INCOMPLETE", "alt com %d caracteres (limite %d)"
              % (len(alt), alt_max), campo="alt")
    if len(hashtags) > hashtag_max:
        _fail("BRIEF_INCOMPLETE", "hashtags com %d itens (limite %d)"
              % (len(hashtags), hashtag_max), campo="hashtags")
    if "min_hashtags" in row:
        hashtag_min = _limit(row, "min_hashtags", 0)
        if len(hashtags) < hashtag_min:
            _fail("BRIEF_INCOMPLETE", "hashtags com %d itens (minimo %d)"
                  % (len(hashtags), hashtag_min), campo="hashtags")
    if "max_chars" in row:
        max_chars = _limit(row, "max_chars", 0)
        if len(legenda) > max_chars:
            _fail("BRIEF_INCOMPLETE", "legenda com %d caracteres (limite %d)"
                  % (len(legenda), max_chars), campo="legenda")
    if row.get("alt_obrigatorio") is True and not alt.strip():
        _fail("BRIEF_INCOMPLETE", "brief.alt nao pode ser vazio", campo="alt")

    cta = brief.get("cta")
    cta_obrigatorio = row.get("cta_obrigatorio") is True
    cta_ok = (isinstance(cta, dict)
              and isinstance(cta.get("texto"), str) and bool(cta["texto"].strip())
              and isinstance(cta.get("destino"), str) and bool(cta["destino"].strip()))
    if cta_obrigatorio and not cta_ok:
        _fail("BRIEF_INCOMPLETE", "brief.cta exige texto e destino nao vazios",
              campo="cta")
    if cta is not None:
        destino = cta.get("destino") if isinstance(cta, dict) else None
        if not (isinstance(destino, str) and destino.startswith("https://")
                and len(destino) > len("https://")):
            _fail("CONFIG_INVALID", "brief.cta.destino deve ser URL https",
                  campo="cta.destino")

    brand = _json(Path(brand_root) / "manifest.json", "manifest da marca")
    source = _safe_file(root, arte)
    hash_record, arte_sha = _approved(root, approvals, arte)
    ia_manifest = _elements(brief, now)

    tag_line = " ".join(tag if tag.startswith("#") else "#" + tag
                        for tag in hashtags)
    manifest = {
        "piece": piece,
        "brand_id": brand_id,
        "format": ident,
        "aprovador": approvals.get("by"),
        "aprovado_em": approvals.get("at"),
        "gerado_em": now or approvals.get("at") or "",
        "hash": dict(hash_record),
        "hashes": {"arte": arte_sha},
        "arte": arte,
        "artefatos": [{"path": arte, "sha256": arte_sha,
                       "bytes": source.stat().st_size}],
        "marca": brand,
    }
    manifest["avisos"] = []
    if brief.get("pessoas") is True:
        if brief.get("consent") is not True:
            manifest["avisos"] = ["BRIEF_CONSENT_PENDING"]
        else:
            responsavel = brief.get("responsavel")
            if isinstance(responsavel, str) and responsavel.strip():
                manifest["consentimento"] = {"responsavel": responsavel}
    if cta_ok:
        manifest["cta"] = {"texto": cta["texto"], "destino": cta["destino"]}

    idioma = brief.get("idioma", "pt-BR")
    grafia_path = Path(brand_root) / "grafia.json"
    if idioma == "pt-BR" and grafia_path.is_file():
        try:
            json.loads(grafia_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _fail("CONFIG_INVALID", "grafia da marca ilegivel: %s" % exc)
        textos = [legenda, alt] + [
            tag[1:] if tag.startswith("#") else tag for tag in hashtags]
        for texto in textos:
            for issue in grafia.check_text(texto, idioma, brand_root):
                if issue["level"] == "error":
                    _fail("GATE_FAILED", issue.get("msg") or issue["code"],
                          campo="grafia", codigo=issue["code"],
                          trecho=issue.get("trecho"))
                if issue["code"] not in manifest["avisos"]:
                    manifest["avisos"].append(issue["code"])

    ent = root / "entrega"
    art_dir = ent / "arte"
    art_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, art_dir / source.name)
    (ent / "legenda.txt").write_text(legenda, encoding="utf-8")
    (ent / "alt.txt").write_text(alt, encoding="utf-8")
    (ent / "hashtags.txt").write_text(tag_line, encoding="utf-8")
    (ent / "horario.json").write_text(
           json.dumps({"sugestao": sugestao, "fuso": fuso},
                      ensure_ascii=False, indent=2) + "\n")
    (ent / "manifesto-ia.json").write_text(
           json.dumps(ia_manifest, ensure_ascii=False, indent=2) + "\n")
    (ent / "manifesto.json").write_text(
           json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest
