import base64
import io
import json
import urllib.error
import wave

import pytest


def _wav_bytes(sr=24000, seconds=0.5):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(b"\x00\x00" * int(sr * seconds))
    return buf.getvalue()


def _payload(wav_bytes):
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "audio/wav",
                                "data": base64.b64encode(wav_bytes).decode("ascii"),
                            }
                        }
                    ]
                }
            }
        ]
    }


def _cfg():
    return {
        "voices": {
            "provider": "gemini",
            "model": "gemini-3.8-flash-tts",
            "api_key_env": "GEMINI_API_KEY",
            "min_tempo": 0.90,
            "max_tempo": 1.20,
            "glossary": {},
            "cast": {
                "narrator": {"voice": "Leda", "style": "calm, warm, measured"},
                "default": {"voice": "Charon", "style": "natural, conversational"},
            },
        }
    }


def _cue(text="hello world", voice="Puck", style="calm"):
    return {
        "id": "A",
        "speaker": "narradora",
        "role": "narrator",
        "t0": 0.0,
        "t1": 1.0,
        "lead": 0.3,
        "text": text,
        "voice": voice,
        "style": style,
    }


class _FakeResponse(dict):
    status = 200
    status_code = 200

    def json(self):
        return dict(self)

    def read(self):
        return json.dumps(dict(self)).encode("utf-8")


def _http_error(code):
    err = urllib.error.HTTPError("https://example.invalid/tts", code, "erro sintetico", {}, None)
    err.status_code = code
    return err


def test_apply_glossary_replaces_only_whole_words():
    from forja import tts

    out = tts.apply_glossary("Marca and Marcason", {"Marca": "Mar-ka"})
    assert out == "Mar-ka and Marcason", "nao deve substituir 'Marca' dentro de 'Marcason'"


def test_apply_glossary_respects_exact_capitalization():
    from forja import tts

    out = tts.apply_glossary("Marca marca MARCA", {"Marca": "Mar-ka"})
    assert out == "Mar-ka marca MARCA", "a chave so casa com a capitalizacao exata"


def test_apply_glossary_handles_punctuation_boundaries():
    from forja import tts

    out = tts.apply_glossary("Marca, meet Marca.", {"Marca": "Mar-ka"})
    assert out == "Mar-ka, meet Mar-ka.", "pontuacao ao redor nao impede a substituicao"


def test_cache_key_is_sha256_hexadecimal():
    from forja import tts

    key = tts.cache_key("gemini", "m", "v", "s", "t")
    assert len(key) == 64 and all(c in "0123456789abcdef" for c in key), "cache_key deve ser sha256 hex"


def test_cache_key_is_deterministic_for_same_inputs():
    from forja import tts

    first = tts.cache_key("gemini", "m", "v", "s", "t")
    second = tts.cache_key("gemini", "m", "v", "s", "t")
    assert first == second, "mesmos argumentos devem gerar a mesma chave"


def test_cache_key_changes_when_text_changes():
    from forja import tts

    first = tts.cache_key("gemini", "m", "v", "s", "um texto")
    second = tts.cache_key("gemini", "m", "v", "s", "outro texto")
    assert first != second, "texto diferente deve gerar chave diferente"


def test_build_gemini_request_returns_url_headers_and_body_without_key():
    from forja import tts

    url, headers, body = tts.build_gemini_request("gemini-3.8-flash-tts", "Puck", "calm", "ola mundo")
    header_names = {str(name).lower() for name in headers}
    dumped = json.dumps(body, ensure_ascii=False)
    assert (
        isinstance(url, str)
        and url.startswith("http")
        and "gemini-3.8-flash-tts" in url
        and "x-goog-api-key" not in header_names
        and "ola mundo" in dumped
    ), "a requisicao deve isolar URL/headers/body e nao embutir a chave"


def test_build_gemini_request_carries_voice_and_style_in_body():
    from forja import tts

    _url, _headers, body = tts.build_gemini_request("modelo-x", "Puck", "calm", "texto")
    dumped = json.dumps(body, ensure_ascii=False)
    assert "Puck" in dumped and "calm" in dumped, "voz e estilo devem ir no body da requisicao"


def test_parse_gemini_response_decodes_last_audio_part():
    from forja import tts

    first = base64.b64encode(b"primeiro").decode("ascii")
    last = base64.b64encode(b"ultimo").decode("ascii")
    resp = {"candidates": [{"content": {"parts": [
        {"inlineData": {"data": first}},
        {"inlineData": {"data": last}},
    ]}}]}
    assert tts.parse_gemini_response(resp) == b"ultimo", "deve decodificar o base64 do ultimo item de audio"


def test_parse_gemini_response_rejects_response_without_audio():
    from forja import tts

    with pytest.raises(ValueError):
        tts.parse_gemini_response({"candidates": [{"content": {"parts": [{"text": "sem audio"}]}}]})


def test_mock_wav_is_mono_pcm_at_requested_rate():
    from forja import tts

    data = tts.mock_wav("um dois tres", sr=24000)
    with wave.open(io.BytesIO(data), "rb") as wav:
        channels, rate, frames = wav.getnchannels(), wav.getframerate(), wav.getnframes()
    assert data[:4] == b"RIFF" and channels == 1 and rate == 24000 and frames > 0, (
        "mock_wav deve ser WAV mono 24 kHz com amostras"
    )


def test_mock_wav_duration_follows_word_estimate():
    from forja import tts

    data = tts.mock_wav("um dois tres quatro cinco seis sete", sr=24000)
    with wave.open(io.BytesIO(data), "rb") as wav:
        duration = wav.getnframes() / float(wav.getframerate())
    assert abs(duration - 7 / 2.8) < 0.15, "duracao do mock deve seguir palavras/2.8"


def test_mock_wav_is_deterministic():
    from forja import tts

    assert tts.mock_wav("mesmo texto") == tts.mock_wav("mesmo texto"), "mesmo texto deve gerar os mesmos bytes"


def test_synthesize_cache_hit_does_not_call_post(tmp_path):
    from forja import tts

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cue = _cue(text="texto em cache")
    cfg = _cfg()
    key = tts.cache_key("gemini", cfg["voices"]["model"], cue["voice"], cue["style"], cue["text"])
    cached = cache_dir / (key + ".wav")
    cached.write_bytes(_wav_bytes())
    calls = []

    def post(*args, **kwargs):
        calls.append(1)
        raise AssertionError("post nao deveria ser chamado em cache hit")

    result = tts.synthesize(cue, cfg, cache_dir, post=post, env={"GEMINI_API_KEY": "x"}, sleep=lambda _s: None)
    assert result == cached and not calls, "cache hit deve devolver o WAV existente sem chamar post"


def test_synthesize_missing_key_raises_forja_error(tmp_path):
    from forja import tts
    from forja.errors import ForjaError

    def post(*args, **kwargs):
        raise AssertionError("post nao deveria ser chamado sem chave")

    with pytest.raises(ForjaError) as excinfo:
        tts.synthesize(_cue(), _cfg(), tmp_path, post=post, env={}, sleep=lambda _s: None)
    assert excinfo.value.code == "MISSING_KEY"
    message = str(excinfo.value)
    assert "GEMINI_API_KEY" in message and "não definida" in message, "erro deve citar a variavel ausente"


def test_synthesize_retries_429_with_backoff(tmp_path):
    from forja import tts

    calls = []
    sleeps = []

    def post(*args, **kwargs):
        calls.append(1)
        raise _http_error(429)

    with pytest.raises((RuntimeError, urllib.error.HTTPError)):
        tts.synthesize(_cue(), _cfg(), tmp_path, post=post, env={"GEMINI_API_KEY": "x"}, sleep=sleeps.append)
    assert len(calls) >= 3 and sleeps[:2] == [1, 2] and all(s in {1, 2, 4} for s in sleeps), (
        "429 deve tentar ao menos 3 vezes com backoff 1, 2, 4"
    )


def test_synthesize_retries_5xx_then_succeeds(tmp_path):
    from forja import tts

    calls = []
    sleeps = []
    payload = _payload(_wav_bytes())

    def post(*args, **kwargs):
        calls.append(1)
        if len(calls) < 3:
            raise _http_error(503)
        return _FakeResponse(payload)

    result = tts.synthesize(_cue(), _cfg(), tmp_path, post=post, env={"GEMINI_API_KEY": "x"}, sleep=sleeps.append)
    assert result.exists() and len(calls) == 3 and sleeps == [1, 2], "5xx deve ser repetido ate a terceira tentativa"


def test_synthesize_does_not_retry_other_4xx(tmp_path):
    from forja import tts

    calls = []
    sleeps = []

    def post(*args, **kwargs):
        calls.append(1)
        raise _http_error(400)

    with pytest.raises((RuntimeError, urllib.error.HTTPError)):
        tts.synthesize(_cue(), _cfg(), tmp_path, post=post, env={"GEMINI_API_KEY": "x"}, sleep=sleeps.append)
    assert len(calls) == 1 and sleeps == [], "4xx diferente de 429 nao deve ser repetido"


def test_synthesize_success_writes_valid_wav(tmp_path):
    from forja import tts

    calls = []
    payload = _payload(_wav_bytes())

    def post(*args, **kwargs):
        calls.append(1)
        return _FakeResponse(payload)

    result = tts.synthesize(_cue(), _cfg(), tmp_path, post=post, env={"GEMINI_API_KEY": "x"}, sleep=lambda _s: None)
    assert result.exists() and result.suffix == ".wav" and result.read_bytes()[:4] == b"RIFF" and len(calls) == 1, (
        "sucesso deve gravar um WAV e chamar post uma vez"
    )


def test_synthesize_missing_key_raises_missing_key_error(tmp_path):
    from forja import tts
    from forja.errors import ForjaError

    cfg = {
        "voices": {
            "provider": "gemini",
            "model": "m",
            "api_key_env": "GEMINI_API_KEY",
            "cast": {"default": {"voice": "X", "style": "s"}},
        }
    }
    with pytest.raises(ForjaError) as excinfo:
        tts.synthesize(
            {"id": "A", "text": "oi"},
            cfg,
            tmp_path,
            post=lambda *args, **kwargs: None,
            env={},
        )
    assert excinfo.value.code == "MISSING_KEY"


def test_provided_wav_reads_a_valid_project_file(tmp_path):
    from forja import tts

    (tmp_path / "voices").mkdir()
    target = tmp_path / "voices" / "A.wav"
    target.write_bytes(tts.mock_wav("oi"))
    cfg = {"voices": {"input_dir": "voices"}}
    assert tts.provided_wav({"id": "A"}, cfg, tmp_path) == target.resolve()


def test_provided_wav_missing_file_is_a_clear_error(tmp_path):
    from forja import tts
    from forja.errors import ForjaError

    (tmp_path / "voices").mkdir()
    with pytest.raises(ForjaError) as excinfo:
        tts.provided_wav({"id": "A"}, {"voices": {"input_dir": "voices"}}, tmp_path)
    assert excinfo.value.code == "MISSING_INPUT"
    assert "voices" in str(excinfo.value)


def test_provided_wav_rejects_an_invalid_file(tmp_path):
    from forja import tts
    from forja.errors import ForjaError

    (tmp_path / "voices").mkdir()
    (tmp_path / "voices" / "A.wav").write_bytes(b"nao e wav")
    with pytest.raises(ForjaError) as excinfo:
        tts.provided_wav({"id": "A"}, {"voices": {"input_dir": "voices"}}, tmp_path)
    assert excinfo.value.code == "CONFIG_INVALID"


def test_source_for_uses_the_files_provider_without_network(tmp_path):
    from forja import tts

    (tmp_path / "voices").mkdir()
    (tmp_path / "voices" / "A.wav").write_bytes(tts.mock_wav("oi"))

    def post(*args, **kwargs):
        raise AssertionError("post nao deveria ser chamado no provider files")

    source = tts.source_for(
        {"id": "A", "text": "oi"},
        {"voices": {"provider": "files", "input_dir": "voices"}},
        tmp_path,
        tmp_path / "cache",
        post=post,
    )
    assert source == (tmp_path / "voices" / "A.wav").resolve()


def test_custom_registered_provider_is_dispatched(tmp_path):
    from forja import registry, tts

    registry.reset_for_tests()
    try:

        @registry.register("tts", "custom-test")
        def factory():
            def synthesize(cue, cfg, cache_dir, post, env):
                assert post is not None
                return tts.mock_wav("custom")

            return synthesize

        cfg = _cfg()
        cfg["voices"]["provider"] = "custom-test"
        cfg["voices"]["model"] = ""
        result = tts.synthesize(
            _cue(),
            cfg,
            tmp_path,
            post=lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("post nao deveria ser chamado")
            ),
        )
        assert result.is_file() and result.read_bytes().startswith(b"RIFF")
    finally:
        registry.reset_for_tests()


def test_piper_provider_writes_a_wav_without_network(tmp_path):
    from types import SimpleNamespace

    from forja import tts

    cfg = _cfg()
    cfg["voices"]["provider"] = "piper"
    cfg["voices"]["piper"] = {
        "binary": "piper",
        "model": "/opt/piper/pt_BR-faber-medium.onnx",
        "length_scale": 1.0,
        "speaker": None,
    }

    def fake_run(cmd, **kwargs):
        assert "--model" in cmd and "--output_file" in cmd
        target = cmd[cmd.index("--output_file") + 1]
        with open(target, "wb") as handle:
            handle.write(tts.mock_wav("oi"))
        return SimpleNamespace(returncode=0, stderr=b"")

    result = tts.synthesize(
        _cue(),
        cfg,
        tmp_path,
        post=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("sem rede")),
        run=fake_run,
    )
    assert result.is_file() and result.read_bytes().startswith(b"RIFF")


def test_piper_missing_binary_is_missing_prereq(tmp_path):
    from forja import tts
    from forja.errors import ForjaError

    cfg = _cfg()
    cfg["voices"]["provider"] = "piper"
    cfg["voices"]["piper"] = {"binary": "piper-inexistente", "model": "/tmp/x.onnx"}

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    with pytest.raises(ForjaError) as excinfo:
        tts.synthesize(_cue(), cfg, tmp_path, post=None, run=fake_run)
    assert excinfo.value.code == "MISSING_PREREQ"


def test_piper_failure_is_provider_error(tmp_path):
    from types import SimpleNamespace

    from forja import tts
    from forja.errors import ForjaError

    cfg = _cfg()
    cfg["voices"]["provider"] = "piper"
    cfg["voices"]["piper"] = {"binary": "piper", "model": "/tmp/x.onnx"}

    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=2, stderr=b"modelo invalido")

    with pytest.raises(ForjaError) as excinfo:
        tts.synthesize(_cue(), cfg, tmp_path, post=None, run=fake_run)
    assert excinfo.value.code == "PROVIDER_ERROR"
    assert "modelo invalido" in str(excinfo.value)


def test_source_for_google_ai_studio_uses_the_same_wav_input(tmp_path):
    from forja import tts

    (tmp_path / "voices").mkdir()
    (tmp_path / "voices" / "A.wav").write_bytes(tts.mock_wav("oi"))
    source = tts.source_for(
        {"id": "A", "text": "oi"},
        {"voices": {"provider": "google_ai_studio", "input_dir": "voices"}},
        tmp_path,
        tmp_path / "cache",
        post=None,
    )
    assert source == (tmp_path / "voices" / "A.wav").resolve()
