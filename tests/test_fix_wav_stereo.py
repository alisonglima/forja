"""Contrato do WAV de voz fornecido pelo usuario (M5).

O caminho padrao (``google_ai_studio``/``files``, ou seja ``provided_wav``)
aceita WAV estéreo e faz downmix para mono PCM 16-bit pela media dos canais,
mantendo a taxa de amostragem original. Mono continua passando byte a byte.
8-bit, 24-bit/float, arquivo que nao e WAV, vazio e 3+ canais continuam
``CONFIG_INVALID``, com ``msg`` apontando o arquivo e ``hint`` descrevendo
exatamente o formato aceito (PCM 16-bit, mono ou estéreo).

Decisao desta lane: 3+ canais sao RECUSADOS (nao ha downmix), com mensagem
citando a quantidade de canais. O caso de polaridade oposta soma ~0: e o
comportamento documentado da media dos canais, nao um bug.
"""
from __future__ import annotations

import io
import struct
import wave

import numpy as np
import pytest

SR = 48000
SECONDS = 0.5
TONE_HZ = 440.0


def _tone(sr=SR, seconds=SECONDS, hz=TONE_HZ, amplitude=0.5, phase=0.0):
    n = int(round(float(sr) * float(seconds)))
    t = np.arange(n, dtype=np.float64) / float(sr)
    samples = np.sin(2.0 * np.pi * float(hz) * t + float(phase)) * float(amplitude)
    return np.rint(samples * 32767.0).astype("<i2")


def _interleave(*channels):
    return np.column_stack(channels).reshape(-1)


def _pcm(samples):
    return np.asarray(samples, dtype="<i2").tobytes()


def _wav_bytes(frames, *, sr=SR, channels=1, sampwidth=2):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(int(channels))
        wav.setsampwidth(int(sampwidth))
        wav.setframerate(int(sr))
        wav.writeframes(frames)
    return buf.getvalue()


def _float_wav_bytes(samples, *, sr=SR, channels=1):
    """WAV IEEE float32 (fmt tag 3), que ``wave``/o pipeline nao aceitam."""
    data = np.asarray(samples, dtype="<f4").tobytes()
    block_align = int(channels) * 4
    header = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
    header += b"fmt " + struct.pack(
        "<IHHIIHH",
        16,
        3,
        int(channels),
        int(sr),
        int(sr) * block_align,
        block_align,
        32,
    )
    header += b"data" + struct.pack("<I", len(data)) + data
    return header


def _cfg():
    return {"voices": {"provider": "google_ai_studio", "input_dir": "voices"}}


def _put_wav(tmp_path, data, cid="A"):
    voices = tmp_path / "voices"
    voices.mkdir(exist_ok=True)
    target = voices / (cid + ".wav")
    target.write_bytes(data)
    return target


def _read_mono(path):
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    samples = np.frombuffer(frames, dtype="<i2")
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, rate, width, channels


def _rms(samples):
    arr = np.asarray(samples, dtype=np.float64)
    return float(np.sqrt(np.mean(arr * arr))) if arr.size else 0.0


def _assert_hint_describes_accepted_formats(hint):
    text = str(hint).lower()
    assert "pcm" in text, "hint deve dizer que o formato aceito e PCM: %r" % hint
    assert "16" in text, "hint deve dizer que o PCM aceito e 16-bit: %r" % hint
    assert "mono" in text, "hint deve dizer que mono e aceito: %r" % hint
    assert "estereo" in text or "estéreo" in text, "hint deve dizer que estéreo e aceito: %r" % hint


# ------------------------------------------------------- estereo e downmix

def test_provided_wav_accepts_stereo_identical_channels_as_mono(tmp_path):
    from forja import tts

    mono = _tone()
    target = _put_wav(
        tmp_path,
        _wav_bytes(_pcm(_interleave(mono, mono)), channels=2),
    )

    result = tts.provided_wav({"id": "A"}, _cfg(), tmp_path)

    assert result == target.resolve(), "deve devolver o mesmo WAV fornecido, ja normalizado"
    out, rate, width, channels = _read_mono(result)
    assert channels == 1, "WAV estéreo deve virar mono"
    assert width == 2, "o downmix deve gravar PCM 16-bit"
    assert rate == SR, "o downmix deve manter a taxa de amostragem original"
    assert len(out) == len(mono), "o downmix nao pode mudar a duracao"
    assert np.max(np.abs(out.astype(np.int64) - mono.astype(np.int64))) <= 1, (
        "canais identicos devem preservar as amostras (media = canal original)"
    )
    assert abs(_rms(out) - _rms(mono)) <= max(1.0, 0.01 * _rms(mono)), (
        "canais identicos devem preservar a energia"
    )


def test_provided_wav_stereo_downmix_averages_the_two_channels(tmp_path):
    from forja import tts

    left = _tone()
    right = np.zeros_like(left)
    target = _put_wav(
        tmp_path,
        _wav_bytes(_pcm(_interleave(left, right)), channels=2),
    )

    result = tts.provided_wav({"id": "A"}, _cfg(), tmp_path)

    out, _rate, _width, channels = _read_mono(result)
    expected = np.rint(left.astype(np.float64) / 2.0).astype(np.int64)
    assert channels == 1
    assert len(out) == len(left)
    assert np.max(np.abs(out.astype(np.int64) - expected)) <= 1, (
        "downmix deve ser a media: canal esquerdo sozinho sai com metade da amplitude"
    )
    assert np.isclose(_rms(out), _rms(left) / 2.0, rtol=0.02), (
        "a energia do canal esquerdo sozinho deve cair para ~1/4 (amplitude pela metade)"
    )


def test_provided_wav_stereo_opposite_polarity_cancels_to_silence(tmp_path):
    from forja import tts

    mono = _tone()
    # Caso documentado: (x + -x) / 2 ~= 0. Nao e falha do kit.
    target = _put_wav(
        tmp_path,
        _wav_bytes(_pcm(_interleave(mono, -mono)), channels=2),
    )

    result = tts.provided_wav({"id": "A"}, _cfg(), tmp_path)

    out, rate, width, channels = _read_mono(result)
    assert (channels, width, rate) == (1, 2, SR)
    assert len(out) == len(mono)
    assert np.max(np.abs(out.astype(np.int64))) <= 1, (
        "canais com polaridade oposta devem somar ~0 no downmix"
    )


def test_normalize_wav_downmixes_stereo_at_the_requested_rate():
    from forja import tts

    mono = _tone()
    stereo = _wav_bytes(_pcm(_interleave(mono, mono)), channels=2)

    out = tts._normalize_wav(stereo, target_sr=SR)

    with wave.open(io.BytesIO(out), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
    assert (channels, width, rate) == (1, 2, SR)
    assert len(samples) == len(mono)
    assert np.max(np.abs(samples.astype(np.int64) - mono.astype(np.int64))) <= 1


# -------------------------------------------------------- mono sem regressao

def test_provided_wav_keeps_mono_bytes_and_rate_unchanged(tmp_path):
    from forja import tts

    data = _wav_bytes(_pcm(_tone()), sr=SR)
    target = _put_wav(tmp_path, data)

    result = tts.provided_wav({"id": "A"}, _cfg(), tmp_path)

    assert result == target.resolve()
    assert result.read_bytes() == data, "mono valido nao pode ser reescrito/reamostrado por provided_wav"


def test_normalize_wav_keeps_mono_bytes_when_rate_matches():
    from forja import tts

    data = _wav_bytes(_pcm(_tone()), sr=SR)
    assert tts._normalize_wav(data, target_sr=SR) == data, "mono na mesma taxa deve continuar byte a byte"


def test_normalize_wav_still_resamples_mono_to_24k():
    from forja import tts

    data = _wav_bytes(_pcm(_tone(seconds=0.25)), sr=SR)

    out = tts._normalize_wav(data)

    with wave.open(io.BytesIO(out), "rb") as wav:
        rate = wav.getframerate()
        duration = wav.getnframes() / float(rate)
    assert rate == 24000, "o pipeline existente continua reamostrando para 24 kHz"
    assert abs(duration - 0.25) < 0.001


def test_synthesize_mock_mono_path_and_cache_key_are_unchanged(tmp_path):
    from forja import tts

    cue = {"id": "A", "text": "oi", "voice": "v", "style": "s"}
    cfg = {"voices": {"provider": "mock", "model": ""}}
    expected_key = tts.cache_key("mock", "", "v", "s", "oi")

    result = tts.synthesize(cue, cfg, tmp_path, post=None)

    assert result == tmp_path / (expected_key + ".wav"), "o hash/caminho de cache mono nao pode mudar"
    assert result.read_bytes() == tts.mock_wav("oi"), "o WAV mono de cache deve continuar identico"


# ----------------------------------------------------------- erros honestos

def _invalid_cases():
    tone = _tone(seconds=0.1)
    n = len(tone)
    return [
        (
            "8-bit-mono",
            lambda: _wav_bytes(b"\x80" * n, channels=1, sampwidth=1),
        ),
        (
            "8-bit-stereo",
            lambda: _wav_bytes(b"\x80" * (n * 2), channels=2, sampwidth=1),
        ),
        (
            "24-bit-mono",
            lambda: _wav_bytes(b"\x00" * (n * 3), channels=1, sampwidth=3),
        ),
        (
            "24-bit-stereo",
            lambda: _wav_bytes(b"\x00" * (n * 6), channels=2, sampwidth=3),
        ),
        (
            "float32-mono",
            lambda: _float_wav_bytes(tone.astype(np.float32) / 32768.0, channels=1),
        ),
        (
            "nao-wav",
            lambda: b"isto nao e um wav",
        ),
        (
            "vazio",
            lambda: b"",
        ),
        (
            "wav-sem-amostras",
            lambda: _wav_bytes(b"", channels=1, sampwidth=2),
        ),
    ]


@pytest.mark.parametrize("case,factory", _invalid_cases(), ids=[c[0] for c in _invalid_cases()])
def test_invalid_wav_formats_are_config_invalid_with_honest_hint(tmp_path, case, factory):
    from forja import tts
    from forja.errors import ForjaError

    target = _put_wav(tmp_path, factory())

    with pytest.raises(ForjaError) as excinfo:
        tts.provided_wav({"id": "A"}, _cfg(), tmp_path)

    exc = excinfo.value
    assert exc.code == "CONFIG_INVALID", "%s deve ser CONFIG_INVALID" % case
    assert str(target.resolve()) in exc.msg, "a msg deve apontar o arquivo invalido"
    _assert_hint_describes_accepted_formats(exc.hint)


def test_three_channel_wav_is_rejected_with_a_clear_message(tmp_path):
    from forja import tts
    from forja.errors import ForjaError

    mono = _tone(seconds=0.1)
    target = _put_wav(
        tmp_path,
        _wav_bytes(_pcm(_interleave(mono, mono, mono)), channels=3),
    )

    with pytest.raises(ForjaError) as excinfo:
        tts.provided_wav({"id": "A"}, _cfg(), tmp_path)

    exc = excinfo.value
    assert exc.code == "CONFIG_INVALID"
    assert str(target.resolve()) in exc.msg
    detail = exc.msg.replace(str(target.resolve()), "").lower()
    assert "canais" in detail and ("3" in detail or "tres" in detail), (
        "3+ canais devem ser recusados com mensagem citando a quantidade de canais: %r" % exc.msg
    )
    _assert_hint_describes_accepted_formats(exc.hint)


def test_invalid_id_is_config_invalid_before_reading_the_wav(tmp_path):
    from forja import tts
    from forja.errors import ForjaError

    (tmp_path / "voices").mkdir()

    with pytest.raises(ForjaError) as excinfo:
        tts.provided_wav({"id": "../A"}, _cfg(), tmp_path)

    exc = excinfo.value
    assert exc.code == "CONFIG_INVALID"
    assert "id da cue" in exc.msg
    assert "estereo" not in exc.hint.lower() and "estéreo" not in exc.hint.lower(), (
        "erro de id nao deve prometer estéreo como formato de WAV"
    )


def test_missing_file_hint_does_not_promise_stereo(tmp_path):
    from forja import tts
    from forja.errors import ForjaError

    (tmp_path / "voices").mkdir()

    with pytest.raises(ForjaError) as excinfo:
        tts.provided_wav({"id": "A"}, _cfg(), tmp_path)

    exc = excinfo.value
    assert exc.code == "MISSING_INPUT"
    assert "A.wav" in exc.msg
    assert "estereo" not in exc.hint.lower() and "estéreo" not in exc.hint.lower(), (
        "erro que nao e de formato nao deve prometer estéreo"
    )
