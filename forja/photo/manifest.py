"""Manifesto deterministico da foto (plano N-23).

Registra hashes de entrada/saida, passos e parametros na ordem de execucao,
marca, origem, licenca e elementos IA, alem da proveniencia opcional (conta,
ferramenta, prompt, data, SynthID/C2PA). Sem timestamp por padrao.
"""
from __future__ import annotations

import copy
import re

from forja.errors import ForjaError

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED = ("input_sha256", "output_sha256", "steps", "brand_id", "origin", "license", "ai_elements")
_TEXT_FIELDS = ("brand_id", "origin", "license")


def _step(item) -> dict:
    if not isinstance(item, dict):
        raise ForjaError("USAGE", "cada passo deve ser um objeto com name e params")
    name = item.get("name")
    params = item.get("params")
    if not isinstance(name, str) or not name:
        raise ForjaError("USAGE", "passo sem nome valido", details={"step": item})
    if not isinstance(params, dict):
        raise ForjaError("USAGE", "params do passo deve ser um objeto",
                         details={"step": name})
    step = dict(item)
    step["name"] = name
    step["params"] = copy.deepcopy(params)
    return step


def build_manifest(*, input_sha256, output_sha256, steps, brand_id, origin, license,
                   ai_elements, **provenance) -> dict:
    """Monta o manifesto da foto preservando passos, parametros e proveniencia."""
    if not isinstance(steps, list):
        raise ForjaError("USAGE", "steps deve ser uma lista de passos")
    if not isinstance(ai_elements, list):
        raise ForjaError("USAGE", "ai_elements deve ser uma lista")
    data = {
        "input_sha256": input_sha256,
        "output_sha256": output_sha256,
        "steps": [_step(item) for item in steps],
        "brand_id": brand_id,
        "origin": origin,
        "license": license,
        "ai_elements": copy.deepcopy(ai_elements),
    }
    for key, value in provenance.items():
        data[key] = copy.deepcopy(value)
    return data


def _issue(code: str, msg: str) -> dict:
    return {"level": "error", "code": code, "msg": msg}


def _is_sha256(value) -> bool:
    return isinstance(value, str) and bool(_SHA256.match(value))


def verify_manifest(data) -> list[dict]:
    """Valida o manifesto e devolve issues `level`/`code`/`msg` (vazio se ok)."""
    if not isinstance(data, dict):
        return [_issue("MANIFEST_TYPE", "manifesto deve ser um objeto JSON")]
    issues = [_issue("MANIFEST_MISSING", f"campo obrigatorio ausente: {key}")
              for key in _REQUIRED if key not in data]
    for key in ("input_sha256", "output_sha256"):
        if key in data and not _is_sha256(data[key]):
            issues.append(_issue("MANIFEST_SHA256",
                                 f"{key} deve ser sha256 hex de 64 caracteres"))
    for key in _TEXT_FIELDS:
        if key in data and (not isinstance(data[key], str) or not data[key]):
            issues.append(_issue("MANIFEST_FIELD",
                                 f"{key} deve ser texto nao vazio"))
    if "ai_elements" in data and not isinstance(data["ai_elements"], list):
        issues.append(_issue("MANIFEST_AI_ELEMENTS",
                             "ai_elements deve ser uma lista"))
    if "steps" in data:
        steps = data["steps"]
        if not isinstance(steps, list):
            issues.append(_issue("MANIFEST_STEPS", "steps deve ser uma lista"))
        else:
            for index, item in enumerate(steps):
                if not isinstance(item, dict):
                    issues.append(_issue("MANIFEST_STEP",
                                         f"passo {index} deve ser um objeto"))
                elif not isinstance(item.get("name"), str) or not item["name"]:
                    issues.append(_issue("MANIFEST_STEP",
                                         f"passo {index} sem nome valido"))
                elif not isinstance(item.get("params"), dict):
                    issues.append(_issue("MANIFEST_STEP",
                                         f"passo {index} sem params validos"))
    return issues
