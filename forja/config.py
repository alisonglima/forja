from __future__ import annotations

import copy
import math
import re
from pathlib import Path

import yaml

from . import registry
from .errors import ForjaError

DEFAULTS: dict = {
    "project": {
        "name": "meu-video",
        "source_lang": "en",
        "target_lang": "pt-BR",
        "require_approvals": False,
    },
    "input": {"video": "input/source.mp4", "start": 0.0, "duration": None},
    "transcribe": {
        "model": "large-v3-turbo",
        "language": "en",
        "compute_type": "int8",
        "vad": True,
    },
    "voices": {
        # "google_ai_studio": padrao; WAVs gerados na interface web do AI Studio, com a sua conta.
        # "files": alias generico para qualquer WAV fornecido pelo usuario.
        # "piper": TTS neural local (sem conta/API), com o modelo pt-BR da imagem.
        # "gemini": API opcional do Google; "mock": tom sintetico para testes.
        "provider": "google_ai_studio",
        "model": "gemini-3.8-flash-tts",
        "api_key_env": "GEMINI_API_KEY",
        "input_dir": "voices",
        "piper": {
            "binary": "piper",
            "model": "/opt/piper/pt_BR-faber-medium.onnx",
            "length_scale": 1.0,
            "speaker": None,
        },
        "min_tempo": 0.90,
        "max_tempo": 1.20,
        "glossary": {},
        "cast": {
            "narrator": {"voice": "", "style": ""},
            "default": {"voice": "", "style": ""},
        },
    },
    "mix": {
        "voice_lufs": -18.0,
        "duck_narrator_db": -20.0,
        "duck_speech_db": -13.0,
        "ramp_s": 0.30,
        "orig_gain": 0.90,
        "target_lufs": -16.0,
        "true_peak": -1.5,
        "lra": 11.0,
    },
    "brand": {
        "primary": "#C24B2A",
        "ink": "#1A1714",
        "paper": "#F6F1E8",
        "accent": "#C24B2A",
        "font": "Liberation Sans",
        "logo": "",
        "safe_margin": 48,
    },
    "render": {
        "width": 1280,
        "height": 720,
        "fps": 30,
        "font_size": 32,
        "max_chars_line": 42,
        "max_lines": 2,
        "cps_max": 20.0,
    },
    "qa": {
        "max_wer": 0.15,
        "max_overlap_frames": 2,
        "lufs_tol": 1.0,
        "max_true_peak": -1.0,
    },
}


class ConfigError(ValueError):
    """Configuracao invalida em config.yaml."""


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def _section(cfg: dict, name: str) -> dict:
    section = cfg.get(name)
    if not isinstance(section, dict):
        raise ConfigError(f"secao '{name}' deve ser um mapeamento")
    return section


def _number(section: dict, section_name: str, key: str, minimum=None, maximum=None):
    value = section.get(key)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ConfigError(
            f"{section_name}.{key} deve ser um numero (recebido {value!r})"
        )
    if minimum is not None and value < minimum:
        raise ConfigError(
            f"{section_name}.{key} deve ser >= {minimum} (recebido {value!r})"
        )
    if maximum is not None and value > maximum:
        raise ConfigError(
            f"{section_name}.{key} deve ser <= {maximum} (recebido {value!r})"
        )
    return value


def _validate(cfg: dict) -> None:
    project = _section(cfg, "project")
    if not isinstance(project.get("require_approvals", False), bool):
        raise ConfigError("project.require_approvals deve ser booleano")
    voices = _section(cfg, "voices")
    provider = voices.get("provider")
    if provider not in ("google_ai_studio", "files", "gemini", "mock", "piper"):
        try:
            registry.get("tts", provider)
        except ForjaError:
            raise ConfigError(
                f"voices.provider invalido: {provider!r} (esperado 'google_ai_studio', 'files', 'piper', 'gemini', 'mock' ou um provedor registrado)"
            ) from None
    input_dir = voices.get("input_dir")
    if not isinstance(input_dir, str) or not input_dir.strip():
        raise ConfigError("voices.input_dir deve ser uma pasta relativa (ex.: 'voices')")
    input_path = Path(input_dir)
    if input_path.is_absolute() or ".." in input_path.parts:
        raise ConfigError("voices.input_dir deve ficar dentro do projeto (sem caminho absoluto nem '..')")
    if provider == "piper":
        piper = voices.get("piper")
        if not isinstance(piper, dict):
            raise ConfigError("voices.piper deve ser um mapeamento quando provider = 'piper'")
        binary = piper.get("binary")
        model = piper.get("model")
        if not isinstance(binary, str) or not binary.strip():
            raise ConfigError("voices.piper.binary deve ser o nome/caminho do executavel piper")
        if not isinstance(model, str) or not model.strip():
            raise ConfigError("voices.piper.model deve ser o caminho do .onnx")
        _number(piper, "voices.piper", "length_scale", 0.5, 2.0)
        speaker = piper.get("speaker")
        if speaker is not None and (isinstance(speaker, bool) or not isinstance(speaker, int) or speaker < 0):
            raise ConfigError("voices.piper.speaker deve ser inteiro >= 0 ou null")
    if provider == "gemini":
        model = voices.get("model")
        if not isinstance(model, str) or not model.strip():
            raise ConfigError("voices.model e obrigatorio quando voices.provider = 'gemini'")
        key_name = voices.get("api_key_env")
        if not isinstance(key_name, str) or not key_name.strip():
            raise ConfigError("voices.api_key_env deve ser o NOME da variavel da chave")
    min_tempo = _number(voices, "voices", "min_tempo", 0.1, 3.0)
    max_tempo = _number(voices, "voices", "max_tempo", 0.1, 3.0)
    inverted = min_tempo > max_tempo
    if inverted:
        raise ConfigError(
            f"voices.min_tempo ({min_tempo}) maior que voices.max_tempo ({max_tempo})"
        )
    brand = _section(cfg, "brand")
    for key in ("primary", "ink", "paper", "accent"):
        color = brand.get(key)
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise ConfigError(f"brand.{key} deve ser uma cor hex #RRGGBB")
    font = brand.get("font")
    if not isinstance(font, str) or not font.strip():
        raise ConfigError("brand.font deve ser o nome de uma fonte instalada")
    logo = brand.get("logo")
    if logo is not None and not isinstance(logo, str):
        raise ConfigError("brand.logo deve ser um caminho relativo ou vazio")
    if isinstance(logo, str) and logo:
        logo_path = Path(logo)
        if logo_path.is_absolute() or ".." in logo_path.parts:
            raise ConfigError("brand.logo deve ficar dentro do projeto (sem caminho absoluto nem '..')")
    margin = brand.get("safe_margin")
    if isinstance(margin, bool) or not isinstance(margin, (int, float)) or not (0 <= float(margin) <= 240):
        raise ConfigError("brand.safe_margin deve ser um numero entre 0 e 240")

    render = _section(cfg, "render")
    _number(render, "render", "fps", 1, 240)
    _number(render, "render", "width", 16, 7680)
    _number(render, "render", "height", 16, 7680)
    _number(render, "render", "font_size", 8, 200)
    _number(render, "render", "max_chars_line", 1, 200)
    _number(render, "render", "max_lines", 1, 10)
    _number(render, "render", "cps_max", 1, 100)

    mix = _section(cfg, "mix")
    _number(mix, "mix", "voice_lufs", -70, 0)
    _number(mix, "mix", "duck_narrator_db", -60, 0)
    _number(mix, "mix", "duck_speech_db", -60, 0)
    _number(mix, "mix", "ramp_s", 0, 5)
    _number(mix, "mix", "orig_gain", 0, 4)
    _number(mix, "mix", "target_lufs", -70, 0)
    _number(mix, "mix", "true_peak", -20, 0)
    _number(mix, "mix", "lra", 1, 50)

    qa_cfg = _section(cfg, "qa")
    _number(qa_cfg, "qa", "max_wer", 0, 1)
    _number(qa_cfg, "qa", "max_overlap_frames", 0, 120)
    _number(qa_cfg, "qa", "lufs_tol", 0, 20)
    _number(qa_cfg, "qa", "max_true_peak", -20, 0)

    input_cfg = _section(cfg, "input")
    _number(input_cfg, "input", "start", 0, None)
    if input_cfg.get("duration") is not None:
        _number(input_cfg, "input", "duration", 0.001, None)


def load_config(path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigError("raiz do config.yaml deve ser um mapeamento")
    cfg = _deep_merge(copy.deepcopy(DEFAULTS), data)
    _validate(cfg)
    return cfg


def write_default_config(path, **overrides) -> None:
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"ja existe: {target}")
    cfg = copy.deepcopy(DEFAULTS)
    for section, values in overrides.items():
        if values is None:
            continue
        if (
            section in cfg
            and isinstance(cfg[section], dict)
            and isinstance(values, dict)
        ):
            cfg[section].update(copy.deepcopy(values))
        else:
            cfg[section] = copy.deepcopy(values)
    if target.parent != Path(".") and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False, allow_unicode=True)
