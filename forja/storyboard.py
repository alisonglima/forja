from __future__ import annotations

import re
from pathlib import Path

from . import ids

LAYER_TYPES = ("clip", "narration", "captions", "card", "music", "sfx", "overlay")
_OVERLAY_PRESETS = ("lower_third", "title", "callout", "quote", "cta", "logo", "stat")
_OVERLAY_POSITIONS = (
    "bottom-left",
    "bottom-right",
    "top-left",
    "top-right",
    "center",
    "bottom-center",
    "top-center",
)
_OVERLAY_DEFAULT_POSITION = {
    "lower_third": "bottom-left",
    "title": "center",
    "callout": "bottom-right",
    "quote": "center",
    "cta": "bottom-center",
    "logo": "top-right",
    "stat": "top-left",
}
_OVERLAY_STYLE_KEYS = (
    "primary",
    "ink",
    "paper",
    "accent",
    "font",
    "font_size",
    "radius",
    "opacity",
    "width",
    "align",
    "uppercase",
    "shadow",
)
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_FITS = ("cover", "contain")
_ASSET_FIELDS = ("file", "asset", "track")
_WORD_RE = re.compile(r"[^\w]+", re.UNICODE)


def _issue(level, scene_id, code, msg):
    return {"level": level, "id": scene_id, "code": code, "msg": msg}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_float(value, default=0.0):
    return float(value) if _is_number(value) else default


def _normalize_word(value):
    if not isinstance(value, str):
        return ""
    return _WORD_RE.sub("", value.lower())


def _word_in_text(word, text):
    target = _normalize_word(word)
    if not target:
        return False
    return any(_normalize_word(token) == target for token in text.split())


def _find_word_start(entries, word):
    target = _normalize_word(word)
    if not target or not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if _normalize_word(entry.get("word")) == target:
            return _as_float(entry.get("start"), 0.0)
    return None


def _narration_text(layers):
    parts = []
    for layer in layers:
        if isinstance(layer, dict) and layer.get("type") == "narration":
            text = layer.get("text")
            if isinstance(text, str):
                parts.append(text)
    return " ".join(parts)


def _has_narration(layers):
    return any(
        isinstance(layer, dict) and layer.get("type") == "narration"
        for layer in layers
    )


def _duration_problem(scene, layers):
    duration = scene.get("duration")
    if not isinstance(duration, dict):
        return "cena sem duration"
    fixed_s = duration.get("fixed_s")
    if _is_number(fixed_s):
        if fixed_s <= 0:
            return "fixed_s deve ser positivo"
        return None
    if duration.get("from") == "narration":
        if not _has_narration(layers):
            return "from: narration sem camada narration"
        return None
    return "duration sem fixed_s nem from: narration"


def _layer_label(layer, scene_id):
    value = layer.get("id")
    return value if value is not None else scene_id


def _asset_target(root, value):
    """Resolve um asset relativo a raiz do projeto; None se sair da raiz."""
    path = Path(value)
    if path.is_absolute():
        return None
    root_path = Path(root).resolve()
    target = (root_path / path).resolve()
    try:
        target.relative_to(root_path)
    except ValueError:
        return None
    return target


def _check_asset(layer, scene_id, root, issues):
    for field in _ASSET_FIELDS:
        value = layer.get(field)
        if not isinstance(value, str) or not value:
            continue
        target = _asset_target(root, value)
        if target is None:
            issues.append(
                _issue(
                    "error",
                    _layer_label(layer, scene_id),
                    "ASSET_OUTSIDE",
                    f"asset fora da raiz do projeto: {value}",
                )
            )
        elif not target.exists():
            issues.append(
                _issue(
                    "error",
                    _layer_label(layer, scene_id),
                    "ASSET_MISSING",
                    f"arquivo nao encontrado: {value}",
                )
            )


def _check_anchors(layer, scene_id, narration_text, issues):
    for key in ("enter", "exit"):
        spec = layer.get(key)
        if not isinstance(spec, dict) or spec.get("anchor") != "word":
            continue
        word = spec.get("word")
        if not _word_in_text(word, narration_text):
            issues.append(
                _issue(
                    "warn",
                    _layer_label(layer, scene_id),
                    "ANCHOR_UNRESOLVED",
                    f"palavra da ancora nao encontrada na narracao: {word!r}",
                )
            )


def _check_overlay(layer, scene_id, issues):
    label = _layer_label(layer, scene_id)
    preset = layer.get("preset")
    if preset not in _OVERLAY_PRESETS:
        issues.append(
            _issue(
                "error",
                label,
                "OVERLAY_PRESET",
                "preset de overlay invalido: %r (use %s)"
                % (preset, ", ".join(_OVERLAY_PRESETS)),
            )
        )
        return

    text = layer.get("text")
    subtext = layer.get("subtext")
    if preset != "logo":
        if not isinstance(text, str) or not text.strip():
            issues.append(
                _issue("error", label, "OVERLAY_TEXT", "overlay %s exige text" % preset)
            )
        elif len(text) > 280:
            issues.append(
                _issue("error", label, "OVERLAY_TEXT", "overlay.text passa de 280 caracteres")
            )
    if subtext is not None and (not isinstance(subtext, str) or len(subtext) > 120):
        issues.append(
            _issue("error", label, "OVERLAY_TEXT", "overlay.subtext deve ter ate 120 caracteres")
        )

    position = layer.get("position", _OVERLAY_DEFAULT_POSITION.get(preset))
    if position not in _OVERLAY_POSITIONS:
        issues.append(
            _issue(
                "error",
                label,
                "OVERLAY_POSITION",
                "posicao de overlay invalida: %r" % (position,),
            )
        )

    if preset == "logo":
        asset = layer.get("asset")
        if not isinstance(asset, str) or not asset:
            issues.append(
                _issue("error", label, "OVERLAY_ASSET", "overlay logo exige asset (PNG/SVG)")
            )

    hold_s = layer.get("hold_s")
    if hold_s is not None and (not _is_number(hold_s) or float(hold_s) <= 0):
        issues.append(
            _issue("error", label, "OVERLAY_HOLD", "overlay.hold_s deve ser positivo")
        )

    style = layer.get("style")
    if style is not None:
        if not isinstance(style, dict):
            issues.append(_issue("error", label, "OVERLAY_STYLE", "overlay.style deve ser mapeamento"))
        else:
            unknown = sorted(set(style) - set(_OVERLAY_STYLE_KEYS))
            if unknown:
                issues.append(
                    _issue(
                        "error",
                        label,
                        "OVERLAY_STYLE",
                        "chaves de estilo desconhecidas: %s" % ", ".join(unknown),
                    )
                )
            for key in ("primary", "ink", "paper", "accent"):
                if key in style and (not isinstance(style[key], str) or not _HEX_RE.match(style[key])):
                    issues.append(
                        _issue("error", label, "OVERLAY_STYLE", f"style.{key} deve ser #RRGGBB")
                    )
            if "font" in style and (not isinstance(style["font"], str) or not style["font"].strip()):
                issues.append(_issue("error", label, "OVERLAY_STYLE", "style.font invalido"))
            if "font_size" in style:
                value = style["font_size"]
                if not _is_number(value) or not (12 <= float(value) <= 200):
                    issues.append(_issue("error", label, "OVERLAY_STYLE", "style.font_size deve ficar entre 12 e 200"))
            if "radius" in style:
                value = style["radius"]
                if not _is_number(value) or not (0 <= float(value) <= 80):
                    issues.append(_issue("error", label, "OVERLAY_STYLE", "style.radius deve ficar entre 0 e 80"))
            if "opacity" in style:
                value = style["opacity"]
                if not _is_number(value) or not (0 <= float(value) <= 1):
                    issues.append(_issue("error", label, "OVERLAY_STYLE", "style.opacity deve ficar entre 0 e 1"))
            if "width" in style:
                value = style["width"]
                if not _is_number(value) or not (40 <= float(value) <= 1200):
                    issues.append(_issue("error", label, "OVERLAY_STYLE", "style.width deve ficar entre 40 e 1200"))
            if "align" in style and style["align"] not in ("left", "center", "right"):
                issues.append(_issue("error", label, "OVERLAY_STYLE", "style.align deve ser left, center ou right"))
            if "uppercase" in style and not isinstance(style["uppercase"], bool):
                issues.append(_issue("error", label, "OVERLAY_STYLE", "style.uppercase deve ser booleano"))
            if "shadow" in style and not isinstance(style["shadow"], bool):
                issues.append(_issue("error", label, "OVERLAY_STYLE", "style.shadow deve ser booleano"))


def validate_storyboard(sb, root=None):
    issues = []
    if not isinstance(sb, dict):
        return [_issue("error", None, "SCHEMA", "storyboard deve ser um mapeamento")]

    version = sb.get("version")
    if not (_is_number(version) and version == 1):
        issues.append(_issue("error", None, "SCHEMA", "version deve ser 1"))

    canvas = sb.get("canvas")
    if not isinstance(canvas, dict):
        issues.append(_issue("error", None, "SCHEMA", "canvas ausente"))
    else:
        for key in ("w", "h", "fps"):
            if key not in canvas:
                issues.append(
                    _issue("error", None, "SCHEMA", f"canvas sem {key}")
                )

    scenes = sb.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        issues.append(_issue("error", None, "SCHEMA", "scenes deve ser lista nao vazia"))
        scenes = scenes if isinstance(scenes, list) else []

    seen = set()
    for scene in scenes:
        if not isinstance(scene, dict):
            issues.append(_issue("error", None, "SCHEMA", "cena deve ser um mapeamento"))
            continue

        scene_id = scene.get("id")
        if scene_id is None or scene_id == "":
            issues.append(_issue("error", None, "SCHEMA", "cena sem id"))
        elif not ids.is_safe_id(scene_id):
            issues.append(
                _issue(
                    "error",
                    scene_id,
                    "BAD_ID",
                    "id de cena invalido para nome de arquivo: %r" % (scene_id,),
                )
            )
        else:
            try:
                duplicated = scene_id in seen
                seen.add(scene_id)
            except TypeError:
                duplicated = False
            if duplicated:
                issues.append(
                    _issue("error", scene_id, "DUP_SCENE", f"id de cena duplicado: {scene_id}")
                )

        layers = scene.get("layers")
        if not isinstance(layers, list):
            issues.append(_issue("error", scene_id, "SCHEMA", "cena sem layers"))
            layers = []

        duration_problem = _duration_problem(scene, layers)
        if duration_problem is not None:
            issues.append(_issue("error", scene_id, "NO_DURATION", duration_problem))

        narration_text = _narration_text(layers)
        for layer in layers:
            if not isinstance(layer, dict):
                issues.append(
                    _issue("error", scene_id, "SCHEMA", "camada deve ser um mapeamento")
                )
                continue
            layer_type = layer.get("type")
            if layer_type is None:
                issues.append(
                    _issue("error", _layer_label(layer, scene_id), "SCHEMA", "camada sem type")
                )
                continue
            if layer_type not in LAYER_TYPES:
                issues.append(
                    _issue(
                        "error",
                        _layer_label(layer, scene_id),
                        "SCHEMA",
                        f"tipo de camada desconhecido: {layer_type}",
                    )
                )
                continue

            if root is not None:
                _check_asset(layer, scene_id, root, issues)

            if layer_type == "overlay":
                _check_overlay(layer, scene_id, issues)

            if layer_type == "music":
                license_info = layer.get("license")
                if not isinstance(license_info, dict) or not license_info.get("kind"):
                    issues.append(
                        _issue(
                            "error",
                            _layer_label(layer, scene_id),
                            "MUSIC_NO_LICENSE",
                            "camada music exige license.kind",
                        )
                    )

            _check_anchors(layer, scene_id, narration_text, issues)

            if "fit" in layer and layer.get("fit") not in _FITS:
                issues.append(
                    _issue(
                        "error",
                        _layer_label(layer, scene_id),
                        "FIT",
                        f"fit invalido: {layer.get('fit')!r} (use cover ou contain)",
                    )
                )

    return issues


def _scene_duration(scene, narration_s):
    duration = scene.get("duration")
    if not isinstance(duration, dict):
        return 0.0
    fixed_s = duration.get("fixed_s")
    if _is_number(fixed_s):
        return float(fixed_s)
    if duration.get("from") == "narration":
        scene_id = scene.get("id")
        base = _as_float(narration_s.get(scene_id), 0.0)
        return (
            _as_float(duration.get("pad_before"), 0.0)
            + base
            + _as_float(duration.get("pad_after"), 0.0)
        )
    return 0.0


def _layer_start(layer, scene_start, scene_end, pad_before, words, scene_id):
    enter = layer.get("enter")
    if not isinstance(enter, dict):
        return scene_start, []
    offset = _as_float(enter.get("offset_s"), 0.0)
    anchor = enter.get("anchor")
    if anchor == "word":
        word_start = _find_word_start(words.get(scene_id), enter.get("word"))
        if word_start is None:
            return scene_start, [f"ancora de palavra nao resolvida: {enter.get('word')!r}"]
        return scene_start + pad_before + word_start + offset, []
    if anchor == "scene_start":
        return scene_start + offset, []
    if anchor == "scene_end":
        return scene_end + offset, []
    at_s = enter.get("at_s")
    if _is_number(at_s):
        return scene_start + float(at_s), []
    return scene_start, []


def resolve_timeline(sb, narration_s, words=None):
    narration_s = narration_s if isinstance(narration_s, dict) else {}
    words = words if isinstance(words, dict) else {}
    canvas = sb.get("canvas") if isinstance(sb, dict) else None
    fps = canvas.get("fps") if isinstance(canvas, dict) else None
    scenes = sb.get("scenes") if isinstance(sb, dict) else None
    if not isinstance(scenes, list):
        scenes = []

    resolved = []
    cursor = 0.0
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        scene_id = scene.get("id")
        duration_s = _scene_duration(scene, narration_s)
        scene_start = cursor
        scene_end = scene_start + duration_s
        cursor = scene_end

        duration = scene.get("duration")
        pad_before = (
            _as_float(duration.get("pad_before"), 0.0)
            if isinstance(duration, dict)
            else 0.0
        )

        layers = scene.get("layers")
        if not isinstance(layers, list):
            layers = []

        out_layers = []
        for layer in layers:
            if not isinstance(layer, dict):
                continue
            out_layer = dict(layer)
            start, warnings = _layer_start(
                layer, scene_start, scene_end, pad_before, words, scene_id
            )
            hold_s = layer.get("hold_s")
            if _is_number(hold_s):
                end = start + float(hold_s)
            else:
                end = scene_end
            if layer.get("type") == "overlay" and end > scene_end:
                end = scene_end
                warnings.append("overlay cortado no fim da cena")
            if (
                layer.get("type") in ("narration", "captions")
                and not isinstance(layer.get("enter"), dict)
                and not _is_number(hold_s)
                and scene_id in narration_s
            ):
                # Fala e legenda ocupam a janela real da narracao, nao o respiro da cena.
                start = scene_start + pad_before
                end = min(scene_end, start + _as_float(narration_s.get(scene_id), 0.0))
            out_layer["start"] = start
            out_layer["end"] = end
            if warnings:
                out_layer["warnings"] = warnings
            out_layers.append(out_layer)

        resolved.append(
            {
                "id": scene_id,
                "start": scene_start,
                "end": scene_end,
                "layers": out_layers,
            }
        )

    return {"fps": fps, "total_s": cursor, "scenes": resolved}


def caption_windows(timeline):
    """Janelas de overlays na parte de baixo que devem levantar a legenda."""
    windows = []
    scenes = timeline.get("scenes") if isinstance(timeline, dict) else None
    if not isinstance(scenes, list):
        return windows
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        layers = scene.get("layers")
        if not isinstance(layers, list):
            continue
        for layer in layers:
            if not isinstance(layer, dict) or layer.get("type") != "overlay":
                continue
            position = str(
                layer.get("position")
                or _OVERLAY_DEFAULT_POSITION.get(layer.get("preset"), "")
            )
            if not position.startswith("bottom"):
                continue
            start = _as_float(layer.get("start"), _as_float(scene.get("start"), 0.0))
            end = _as_float(layer.get("end"), _as_float(scene.get("end"), start))
            if end > start:
                windows.append([start, end])
    return windows


def _timestamp(seconds):
    total_ms = int(round(_as_float(seconds, 0.0) * 1000))
    if total_ms < 0:
        total_ms = 0
    hours, remainder = divmod(total_ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def to_srt(timeline, texts):
    texts = texts if isinstance(texts, dict) else {}
    scenes = timeline.get("scenes") if isinstance(timeline, dict) else None
    if not isinstance(scenes, list):
        return ""

    blocks = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        captions = None
        layers = scene.get("layers")
        if isinstance(layers, list):
            for layer in layers:
                if isinstance(layer, dict) and layer.get("type") == "captions":
                    captions = layer
                    break
        if captions is None:
            continue

        lines = texts.get(scene.get("id"))
        if not lines:
            continue
        start = captions.get("start", scene.get("start", 0.0))
        end = captions.get("end", scene.get("end", start))
        text = "\n".join(str(line) for line in lines)
        blocks.append(
            f"{len(blocks) + 1}\n{_timestamp(start)} --> {_timestamp(end)}\n{text}"
        )

    return "\n\n".join(blocks)
