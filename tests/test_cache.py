"""Contratos de forja.cache descritos no DESIGN.md."""
import json
import re

import pytest


def _sha256_hex(value):
    return re.fullmatch(r"[0-9a-f]{64}", value) is not None


def test_hash_inputs_returns_sha256_hex(tmp_path):
    from forja import cache

    path = tmp_path / "entrada.txt"
    path.write_text("conteudo", encoding="utf-8")
    assert _sha256_hex(cache.hash_inputs([path]))


def test_hash_inputs_is_deterministic(tmp_path):
    from forja import cache

    path = tmp_path / "entrada.txt"
    path.write_text("conteudo", encoding="utf-8")
    assert cache.hash_inputs([path]) == cache.hash_inputs([path])


def test_hash_inputs_changes_with_content_of_same_size(tmp_path):
    from forja import cache

    path = tmp_path / "entrada.txt"
    path.write_text("aaaa", encoding="utf-8")
    before = cache.hash_inputs([path])
    path.write_text("bbbb", encoding="utf-8")
    assert cache.hash_inputs([path]) != before


def test_hash_inputs_changes_when_missing_file_appears(tmp_path):
    from forja import cache

    path = tmp_path / "entrada.txt"
    missing = cache.hash_inputs([path])
    path.write_text("conteudo", encoding="utf-8")
    assert cache.hash_inputs([path]) != missing


def test_hash_inputs_is_order_independent(tmp_path):
    from forja import cache

    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")
    assert cache.hash_inputs([first, second]) == cache.hash_inputs([second, first])


def test_hash_inputs_changes_with_extra(tmp_path):
    from forja import cache

    path = tmp_path / "entrada.txt"
    path.write_text("conteudo", encoding="utf-8")
    assert cache.hash_inputs([path], {"model": "v1"}) != cache.hash_inputs(
        [path], {"model": "v2"}
    )


def test_hash_inputs_canonicalizes_extra_key_order():
    from forja import cache

    assert cache.hash_inputs([], {"a": 1, "b": 2}) == cache.hash_inputs(
        [], {"b": 2, "a": 1}
    )


def test_hash_inputs_changes_with_nested_extra_value():
    from forja import cache

    assert cache.hash_inputs([], {"cfg": {"a": 1}}) != cache.hash_inputs(
        [], {"cfg": {"a": 2}}
    )


def test_hash_inputs_distinguishes_file_names_with_same_content(tmp_path):
    from forja import cache

    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("igual", encoding="utf-8")
    second.write_text("igual", encoding="utf-8")
    assert cache.hash_inputs([first]) != cache.hash_inputs([second])


def test_hash_inputs_supports_no_paths():
    from forja import cache

    assert _sha256_hex(cache.hash_inputs([]))


def test_manifest_get_unknown_step_returns_none(tmp_path):
    from forja import cache

    assert cache.Manifest(tmp_path / "manifest.json").get("nope") is None


def test_manifest_put_then_get_returns_entry(tmp_path):
    from forja import cache

    out = tmp_path / "saida.txt"
    out.write_text("x", encoding="utf-8")
    manifest = cache.Manifest(tmp_path / "manifest.json")
    manifest.put("voices", "hash-1", [str(out)])
    entry = manifest.get("voices")
    assert (entry["input_hash"], entry["outputs"]) == ("hash-1", [str(out)])


def test_manifest_save_writes_readable_json(tmp_path):
    from forja import cache

    path = tmp_path / "manifest.json"
    manifest = cache.Manifest(path)
    manifest.put("voices", "hash-1", [])
    manifest.save()
    assert "voices" in json.loads(path.read_text(encoding="utf-8"))


def test_manifest_is_fresh_true_when_hash_matches_and_outputs_exist(tmp_path):
    from forja import cache

    out = tmp_path / "saida.txt"
    out.write_text("x", encoding="utf-8")
    manifest = cache.Manifest(tmp_path / "manifest.json")
    manifest.put("voices", "hash-1", [str(out)])
    manifest.save()
    assert manifest.is_fresh("voices", "hash-1", [str(out)]) is True


def test_manifest_is_fresh_false_when_hash_differs(tmp_path):
    from forja import cache

    out = tmp_path / "saida.txt"
    out.write_text("x", encoding="utf-8")
    manifest = cache.Manifest(tmp_path / "manifest.json")
    manifest.put("voices", "hash-1", [str(out)])
    manifest.save()
    assert manifest.is_fresh("voices", "hash-2", [str(out)]) is False


def test_manifest_is_fresh_false_when_an_output_is_missing(tmp_path):
    from forja import cache

    out = tmp_path / "saida.txt"
    out.write_text("x", encoding="utf-8")
    manifest = cache.Manifest(tmp_path / "manifest.json")
    manifest.put("voices", "hash-1", [str(out)])
    manifest.save()
    out.unlink()
    assert manifest.is_fresh("voices", "hash-1", [str(out)]) is False


def test_manifest_is_fresh_false_for_unknown_step(tmp_path):
    from forja import cache

    manifest = cache.Manifest(tmp_path / "manifest.json")
    assert manifest.is_fresh("nope", "hash-1", []) is False


def test_manifest_persists_across_instances(tmp_path):
    from forja import cache

    path = tmp_path / "manifest.json"
    out = tmp_path / "saida.txt"
    out.write_text("x", encoding="utf-8")
    first = cache.Manifest(path)
    first.put("voices", "hash-1", [str(out)])
    first.save()
    second = cache.Manifest(path)
    assert second.is_fresh("voices", "hash-1", [str(out)]) is True


def test_manifest_ignores_corrupted_json(tmp_path):
    from forja import cache

    path = tmp_path / "manifest.json"
    path.write_text("{isto nao e json", encoding="utf-8")
    assert cache.Manifest(path).get("voices") is None


def test_manifest_missing_file_is_empty(tmp_path):
    from forja import cache

    assert cache.Manifest(tmp_path / "ausente.json").get("voices") is None


def test_manifest_save_leaves_a_valid_json_and_no_temporary_file(tmp_path):
    from forja import cache

    path = tmp_path / "manifest.json"
    manifest = cache.Manifest(path)
    manifest.put("voices", "hash", [])
    manifest.save()
    assert path.is_file()
    assert not path.with_name(path.name + ".tmp").exists()
    assert json.loads(path.read_text(encoding="utf-8"))["voices"]["input_hash"] == "hash"
