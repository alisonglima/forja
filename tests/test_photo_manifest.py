"""Contrato `forja.photo.manifest` (L-T-PM-01, plano:847): `build_manifest(...) -> dict`,
`verify_manifest(data) -> list[dict]` (plano:776); issues `level`/`code`/`msg`, params livres (plano:781).
Conteudo `input_sha256`, `output_sha256`, passos+params ordenados, `brand_id`, origem, licenca,
elementos IA; deterministico sem timestamp (plano:746); SynthID/C2PA registrados (plano:99).
Impl N-23 L-PHOTO-MAN-01 (plano:815).
# LACUNA: DESIGN.md nao define este modulo; kwargs/codes exatos livres.
"""


def _args():
    return {"input_sha256": "a" * 64, "output_sha256": "b" * 64,
            "steps": [{"name": "crop", "params": {"focal": [0.5, 0.5]}}],
            "brand_id": "leo-lions", "origin": "local", "license": "CC0", "ai_elements": []}


def _error_issues(issues):
    assert isinstance(issues, list) and issues
    for issue in issues:
        assert {"level", "code", "msg"} <= set(issue) and issue["level"] == "error"
        assert isinstance(issue["code"], str) and issue["code"]
        assert isinstance(issue["msg"], str) and issue["msg"]


def test_build_manifest_returns_dict_with_documented_fields():
    from forja.photo import manifest
    data = manifest.build_manifest(**_args())
    assert isinstance(data, dict)
    assert (data["input_sha256"], data["output_sha256"]) == ("a" * 64, "b" * 64)
    assert (data["brand_id"], data["origin"], data["license"], data["ai_elements"]) == ("leo-lions", "local", "CC0", [])


def test_build_manifest_keeps_steps_ordered_with_params():
    from forja.photo import manifest
    steps = [{"name": "crop", "params": {"focal": [0.5, 0.5]}}, {"name": "duotone", "params": {"alpha": 0.5}}]
    data = manifest.build_manifest(**{**_args(), "steps": steps})
    assert [s["name"] for s in data["steps"]] == ["crop", "duotone"]
    assert data["steps"][0]["params"] == {"focal": [0.5, 0.5]} and data["steps"][1]["params"] == {"alpha": 0.5}


def test_build_manifest_is_deterministic():
    from forja.photo import manifest
    assert manifest.build_manifest(**_args()) == manifest.build_manifest(**_args())


def test_build_manifest_registers_provenance_without_removing():
    from forja.photo import manifest
    data = manifest.build_manifest(**{**_args(), "origin": "flow", "account": "1", "tool": "flow",
                                      "prompt": "retrato noturno", "date": "2026-11-11",
                                      "synthid": "presente", "c2pa": {"presente": True}})
    assert (data["origin"], data["account"], data["tool"]) == ("flow", "1", "flow")
    assert (data["prompt"], data["date"], data["synthid"]) == ("retrato noturno", "2026-11-11", "presente")
    assert data["c2pa"] == {"presente": True}


def test_verify_manifest_accepts_built_manifest():
    from forja.photo import manifest
    assert manifest.verify_manifest(manifest.build_manifest(**_args())) == []


def test_verify_manifest_rejects_empty_dict():
    from forja.photo import manifest
    _error_issues(manifest.verify_manifest({}))


def test_verify_manifest_rejects_missing_input_sha256():
    from forja.photo import manifest
    data = manifest.build_manifest(**_args())
    del data["input_sha256"]
    _error_issues(manifest.verify_manifest(data))


def test_verify_manifest_rejects_malformed_sha256():
    from forja.photo import manifest
    data = manifest.build_manifest(**_args())
    data["output_sha256"] = 12345
    _error_issues(manifest.verify_manifest(data))


def test_verify_manifest_rejects_non_dict_input():
    from forja.photo import manifest
    _error_issues(manifest.verify_manifest(None))
    _error_issues(manifest.verify_manifest("{quebrado"))


def test_verify_manifest_rejects_steps_of_wrong_type():
    from forja.photo import manifest
    data = manifest.build_manifest(**_args())
    data["steps"] = "crop"
    _error_issues(manifest.verify_manifest(data))
