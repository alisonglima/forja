from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import time
import urllib.error
import wave
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

import numpy as np

from . import ids
from .errors import ForjaError

_TARGET_SR = 24000
_WORDS_PER_SECOND = 2.8
_ATTEMPTS = 3


def _estimate_duration_s(text: str) -> float:
    """Estimativa local de duracao (mesma regra de cues.py): palavras / 2.8."""
    return len(str(text).split()) / _WORDS_PER_SECOND


def apply_glossary(text: str, glossary: Mapping[str, str]) -> str:
    """Substitui palavras inteiras do glossario, respeitando maiusculas exatas."""
    if not glossary:
        return text
    keys = sorted(glossary, key=len, reverse=True)
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(k) for k in keys) + r")(?!\w)")
    return pattern.sub(lambda match: str(glossary[match.group(0)]), text)


def cache_key(provider: str, model: str, voice: str, style: str, text: str) -> str:
    """sha256 hex de um JSON canonico com os parametros da sintese."""
    canonical = json.dumps(
        [provider, model, voice, style, text],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_gemini_request(model: str, voice: str, style: str, text: str) -> tuple[str, dict, dict]:
    """Monta (url, headers sem chave, body) para a API Gemini de TTS.

    Todo o formato da API fica isolado nesta funcao; o chamador adiciona a
    chave no header ``x-goog-api-key``.
    """
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + str(model)
        + ":generateContent"
    )
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{"role": "user", "parts": [{"text": str(text)}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": str(voice)}},
                "style": str(style),
            },
        },
    }
    return url, headers, body


def parse_gemini_response(resp: dict) -> bytes:
    """Decodifica o base64 do ultimo item de audio da resposta Gemini."""
    parts_audio: list[str] = []
    for candidate in resp.get("candidates") or []:
        content = candidate.get("content") or {}
        for part in content.get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if isinstance(inline, Mapping) and inline.get("data"):
                parts_audio.append(str(inline["data"]))
    if not parts_audio:
        raise ValueError("resposta do Gemini sem item de audio")
    return base64.b64decode(parts_audio[-1])


def _wav_bytes(pcm: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(int(sr))
        wav.writeframes(np.asarray(pcm, dtype="<i2").tobytes())
    return buf.getvalue()


def mock_wav(text: str, sr: int = _TARGET_SR) -> bytes:
    """Tom deterministico mono PCM 16-bit com duracao estimada do texto."""
    duration = _estimate_duration_s(text)
    n = int(round(duration * int(sr)))
    if n <= 0:
        n = 1
    t = np.arange(n, dtype=np.float64) / float(sr)
    samples = np.sin(2.0 * np.pi * 220.0 * t) * 0.2
    fade = min(n // 2, int(0.01 * int(sr)))
    if fade > 0:
        envelope = np.ones(n, dtype=np.float64)
        envelope[:fade] = np.linspace(0.0, 1.0, fade)
        envelope[-fade:] = np.linspace(1.0, 0.0, fade)
        samples *= envelope
    pcm = np.clip(np.rint(samples * 32767.0), -32768, 32767).astype("<i2")
    return _wav_bytes(pcm, sr)


def _read_wav(data: bytes) -> tuple[np.ndarray, int]:
    if data[:4] != b"RIFF":
        raise RuntimeError("WAV invalido: cabecalho RIFF ausente")
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            channels = wav.getnchannels()
            width = wav.getsampwidth()
            rate = wav.getframerate()
            frames = wav.readframes(wav.getnframes())
    except (wave.Error, EOFError) as exc:
        raise RuntimeError("WAV invalido: " + str(exc)) from exc
    if channels != 1:
        raise RuntimeError("WAV deve ser mono")
    if not frames:
        raise RuntimeError("WAV sem amostras")
    if width != 2:
        raise RuntimeError("WAV deve ser PCM 16-bit")
    return np.frombuffer(frames, dtype="<i2").astype(np.float64), rate


def _resample(samples: np.ndarray, sr: int, target_sr: int) -> np.ndarray:
    if sr == target_sr or len(samples) == 0:
        return samples
    n_out = int(round(len(samples) * float(target_sr) / float(sr)))
    if n_out <= 0:
        n_out = 1
    old_x = np.arange(len(samples), dtype=np.float64)
    new_x = np.linspace(0.0, float(len(samples) - 1), n_out)
    return np.interp(new_x, old_x, samples)


def _normalize_wav(data: bytes, target_sr: int = _TARGET_SR) -> bytes:
    """Valida (RIFF, mono, com amostras) e reamostra para target_sr."""
    samples, sr = _read_wav(data)
    if sr == target_sr:
        return data
    resampled = _resample(samples, sr, target_sr)
    pcm = np.clip(np.rint(resampled), -32768, 32767).astype("<i2")
    return _wav_bytes(pcm, target_sr)


def _status_of(value: Any) -> int | None:
    for name in ("status_code", "status", "code"):
        status = getattr(value, name, None)
        if isinstance(status, int):
            return status
    return None


def _response_json(resp: Any) -> dict:
    json_method = getattr(resp, "json", None)
    if callable(json_method):
        return json_method()
    read = getattr(resp, "read", None)
    if callable(read):
        return json.loads(read())
    if isinstance(resp, Mapping):
        return dict(resp)
    raise RuntimeError("resposta do TTS sem JSON")


def _resolve_voice(cue: Mapping[str, Any], voices_cfg: Mapping[str, Any]) -> tuple[str, str]:
    cast = voices_cfg.get("cast") or {}
    role = str(cue.get("role", "speech"))
    fallback = cast.get(role) or cast.get("default") or {}
    voice = cue.get("voice") or fallback.get("voice") or ""
    style = cue.get("style") or fallback.get("style") or ""
    return str(voice), str(style)


def _post_once(
    post: Callable[..., Any],
    url: str,
    headers: dict,
    body: dict,
) -> bytes:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    resp = post(url, headers=headers, body=payload)
    status = _status_of(resp)
    if status is not None and status >= 400:
        raise urllib.error.HTTPError(url, status, "erro HTTP do TTS", {}, None)
    return parse_gemini_response(_response_json(resp))


def input_dir(cfg: dict) -> str:
    voices_cfg = cfg.get("voices") or {}
    return str(voices_cfg.get("input_dir") or "voices")


def provided_wav(cue: dict, cfg: dict, root) -> Path:
    """WAV fornecido pelo usuario em <projeto>/<voices.input_dir>/<id>.wav."""
    cid = ids.require_safe_id(cue.get("id"), "id da cue")
    root_path = Path(root).resolve()
    target = (root_path / input_dir(cfg) / (cid + ".wav")).resolve()
    try:
        target.relative_to(root_path)
    except ValueError:
        raise ForjaError(
            "CONFIG_INVALID",
            "caminho de voz fora do projeto: %s" % target,
            hint="voices.input_dir deve ficar dentro do projeto",
        ) from None
    if not target.is_file():
        raise ForjaError(
            "MISSING_INPUT",
            "voz nao encontrada: %s" % target,
            hint="gere a voz com a sua conta/ferramenta e salve o WAV nesse caminho",
            details={"path": str(target), "cue": cid},
        )
    try:
        _normalize_wav(target.read_bytes())
    except RuntimeError as exc:
        raise ForjaError(
            "CONFIG_INVALID",
            "WAV invalido em %s: %s" % (target, exc),
            hint="use um WAV PCM mono ou estereo valido",
            details={"path": str(target), "cue": cid},
        ) from exc
    return target


def source_for(cue: dict, cfg: dict, root, cache_dir: Path, post, env=None, sleep=time.sleep) -> Path:
    """Resolve a fonte da voz: arquivo fornecido pelo usuario ou provedor."""
    provider = str((cfg.get("voices") or {}).get("provider", "files"))
    if provider == "files":
        return provided_wav(cue, cfg, root)
    return synthesize(cue, cfg, cache_dir, post, env=env, sleep=sleep)


def synthesize(
    cue: dict,
    cfg: dict,
    cache_dir: Path,
    post: Callable[..., Any],
    env: Mapping[str, str] | None = None,
    sleep: Callable[[float], Any] = time.sleep,
) -> Path:
    """Sintetiza um cue, usando cache; devolve o caminho do WAV em cache."""
    if env is None:
        env = os.environ
    voices_cfg = cfg.get("voices") or {}
    provider = str(voices_cfg.get("provider", "gemini"))
    model = str(voices_cfg.get("model", ""))
    voice, style = _resolve_voice(cue, voices_cfg)
    text = apply_glossary(str(cue.get("text", "")), voices_cfg.get("glossary") or {})
    key = cache_key(provider, model, voice, style, text)
    directory = Path(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (key + ".wav")

    if path.exists():
        cached = path.read_bytes()
        try:
            normalized = _normalize_wav(cached)
        except RuntimeError:
            pass
        else:
            if normalized != cached:
                path.write_bytes(normalized)
            return path

    if provider == "mock":
        wav_data = mock_wav(text)
    else:
        key_name = str(voices_cfg.get("api_key_env", "GEMINI_API_KEY"))
        api_key = env.get(key_name) if env is not None else None
        if not api_key:
            raise ForjaError(
                "MISSING_KEY",
                "variável " + key_name + " não definida",
                hint="defina a chave no .env (o valor nunca deve ir para o projeto ou para o log)",
            )
        url, headers, body = build_gemini_request(model, voice, style, text)
        headers = dict(headers)
        headers["x-goog-api-key"] = api_key
        wav_data = b""
        for attempt in range(_ATTEMPTS):
            try:
                wav_data = _post_once(post, url, headers, body)
                break
            except Exception as exc:
                status = _status_of(exc)
                retryable = status == 429 or (status is not None and 500 <= status < 600)
                if not retryable:
                    raise
                if attempt == _ATTEMPTS - 1:
                    raise RuntimeError(
                        "falha ao sintetizar apos "
                        + str(_ATTEMPTS)
                        + " tentativas (HTTP "
                        + str(status)
                        + ")"
                    ) from exc
                sleep(2 ** attempt)
        if not wav_data:
            raise RuntimeError("falha ao sintetizar: resposta vazia")

    path.write_bytes(_normalize_wav(wav_data))
    return path
