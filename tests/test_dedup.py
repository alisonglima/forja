"""Contrato de `forja.dedup` (congela N-17 `L-DEDUP-01`).
plano:742: sha256 em streaming; registro `{hash,path,scope,piece,at}`; `text_hash`
normaliza legenda (minusculas, sem URL/hashtag, espacos colapsados); `perceptual_hash`
(dHash) pega arte recomprimida; `find_duplicate` usa janela de 30 dias e o mesmo
`scope`; `record` poda antigos e grava atomico.
plano:770: `content_hash`, `text_hash`, `perceptual_hash`, `find_duplicate`, `record`.
`DUPLICATE_ARTIFACT` (exit 1) e emitido por `qa_visual.py`, nao por este modulo.
LACUNA: assinatura completa de `record(...)`; topo do JSON de registro; atomicidade
(so o estado final); borda exata dos 30 dias; rejeicao de path com `..`.
"""
import datetime
import hashlib
import json
from pathlib import Path
import pytest

def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path
def _image(path, pattern):
    from PIL import Image
    on = (lambda x, _y: x < 32) if pattern == "split" else (lambda x, y: (x // 8 + y // 8) % 2)
    img = Image.new("RGB", (64, 64))
    img.putdata([(255, 255, 255) if on(x, y) else (0, 0, 0) for y in range(64) for x in range(64)])
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=95, subsampling=0) if path.suffix == ".jpg" else img.save(path)
    return path
def _at(day):
    return datetime.datetime(2026, 1, day, 12, tzinfo=datetime.timezone.utc)

def test_content_hash_is_sha256_streamed_and_rejects_missing(tmp_path):
    from forja import dedup
    data = bytes(range(256)) * 4097
    art = _write(tmp_path / "art.bin", data)
    assert dedup.content_hash(art) == hashlib.sha256(data).hexdigest()
    other = _write(tmp_path / "other.bin", data + b"x")
    assert dedup.content_hash(art) != dedup.content_hash(other)
    with pytest.raises(Exception):
        dedup.content_hash(tmp_path / "missing.bin")
    # LACUNA: tipo de excecao para arquivo ausente nao decidido.

def test_text_hash_normalizes_case_url_hashtag_spaces_and_edges():
    from forja import dedup
    expected = dedup.text_hash("veja agora")
    assert dedup.text_hash("  VEJA   Agora  ") == expected
    assert dedup.text_hash("veja https://exemplo.test/a?b=1 agora") == expected
    assert dedup.text_hash("veja #Lions agora") == expected
    assert dedup.text_hash("") == dedup.text_hash("   \n\t ")
    assert dedup.text_hash("uma legenda") != dedup.text_hash("outra legenda")

def test_find_duplicate_matches_content_and_recompressed_art(tmp_path):
    from forja import dedup
    now = _at(11)
    original = _image(tmp_path / "out" / "original.png", "split")
    copy = _write(tmp_path / "input" / "copy.png", original.read_bytes())
    jpg = _image(tmp_path / "input" / "recompressed.jpg", "split")
    checker = _image(tmp_path / "checker.png", "checker")
    assert dedup.perceptual_hash(original) == dedup.perceptual_hash(jpg)
    assert dedup.content_hash(original) != dedup.content_hash(jpg)
    assert dedup.perceptual_hash(original) != dedup.perceptual_hash(checker)
    assert dedup.find_duplicate(tmp_path, copy, scope="marca-a", now=now) is None
    dedup.record(tmp_path, original, scope="marca-a", now=now)
    entry = dedup.find_duplicate(tmp_path, copy, scope="marca-a", now=now)
    assert entry is not None and entry["hash"] == dedup.content_hash(original)
    path = Path(entry["path"])
    assert (path if path.is_absolute() else tmp_path / path).resolve() == original.resolve()
    assert "2026-01-11" in entry["at"]
    assert dedup.find_duplicate(tmp_path, jpg, scope="marca-a", now=now) is not None

def test_find_duplicate_filters_scope_and_30_day_window(tmp_path):
    from forja import dedup
    art = _image(tmp_path / "arte.png", "split")
    dedup.record(tmp_path, art, scope="marca-a", now=_at(1))
    assert dedup.find_duplicate(tmp_path, art, scope="marca-b", now=_at(25)) is None
    found = dedup.find_duplicate(tmp_path, art, scope="marca-a", now=_at(25))
    assert found is not None and found["scope"] == "marca-a" and found["hash"] == dedup.content_hash(art)
    assert dedup.find_duplicate(tmp_path, art, scope="marca-a", now=_at(40)) is None

def test_record_prunes_old_entries_and_writes_valid_json(tmp_path):
    from forja import dedup
    old = _image(tmp_path / "old.png", "split")
    new = _image(tmp_path / "new.png", "checker")
    dedup.record(tmp_path, old, scope="marca-a", now=_at(1))
    dedup.record(tmp_path, new, scope="marca-a", now=_at(40))
    registry = tmp_path / "work" / "hashes.json"
    payload = json.dumps(json.loads(registry.read_text(encoding="utf-8")))
    assert dedup.content_hash(new) in payload
    assert dedup.content_hash(old) not in payload
    assert all(field in payload for field in ("hash", "path", "scope", "piece", "at"))
    assert [p.name for p in registry.parent.iterdir()] == ["hashes.json"]
    assert dedup.find_duplicate(tmp_path, old, scope="marca-a", now=_at(40)) is None

def test_find_duplicate_fails_closed_on_truncated_registry(tmp_path):
    from forja import dedup
    art = _image(tmp_path / "arte.png", "split")
    bad = _write(tmp_path / "hashes.json", b'{"hash": "abc')
    with pytest.raises(Exception):
        dedup.find_duplicate(tmp_path, art, registry_path=bad)
    # LACUNA: codigo de erro para JSON invalido nao decidido (falha fechada).
