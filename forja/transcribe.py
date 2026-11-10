from __future__ import annotations


def _norm_text(value) -> str:
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    return value.strip()


def normalize_segments(raw: list[dict]) -> dict:
    segments: list[dict] = []
    for item in list(raw or []):
        if not isinstance(item, dict):
            continue
        start = item.get("start", 0.0)
        end = item.get("end", 0.0)
        try:
            start_f = float(start)
        except (TypeError, ValueError):
            start_f = 0.0
        try:
            end_f = float(end)
        except (TypeError, ValueError):
            end_f = 0.0
        if start_f > end_f:
            start_f, end_f = end_f, start_f
        text = _norm_text(item.get("text", ""))
        if not text:
            continue
        raw_words = item.get("words", [])
        if raw_words is None:
            raw_words = []
        words: list[dict] = []
        if isinstance(raw_words, list):
            for w in raw_words:
                if not isinstance(w, dict):
                    continue
                wtext = _norm_text(w.get("word", ""))
                if not wtext:
                    continue
                wstart = w.get("start", 0.0)
                wend = w.get("end", 0.0)
                try:
                    wstart_f = float(wstart)
                except (TypeError, ValueError):
                    wstart_f = 0.0
                try:
                    wend_f = float(wend)
                except (TypeError, ValueError):
                    wend_f = 0.0
                if wstart_f > wend_f:
                    wstart_f, wend_f = wend_f, wstart_f
                words.append({"word": wtext, "start": wstart_f, "end": wend_f})
        segments.append({"start": start_f, "end": end_f, "text": text, "words": words})
    duration = 0.0
    for seg in segments:
        if seg["end"] > duration:
            duration = float(seg["end"])
    return {"language": "en", "duration": duration, "segments": segments}


def _resolve_model(name) -> str:
    if name == "large-v3-turbo":
        return "deepdml/faster-whisper-large-v3-turbo-ct2"
    return name


def run_transcribe(wav, cfg, model_dir) -> dict:
    from faster_whisper import WhisperModel

    tcfg = {}
    if isinstance(cfg, dict):
        inner = cfg.get("transcribe", cfg)
        if isinstance(inner, dict):
            tcfg = inner
    model_name = tcfg.get("model", "large-v3-turbo")
    language = tcfg.get("language", "en")
    compute_type = tcfg.get("compute_type", "int8")
    vad = tcfg.get("vad", True)
    resolved = _resolve_model(model_name)
    kwargs = {"compute_type": compute_type}
    if model_dir is not None:
        kwargs["download_root"] = str(model_dir)
    model = WhisperModel(resolved, **kwargs)
    segs, info = model.transcribe(str(wav), language=language, vad_filter=bool(vad), word_timestamps=True)
    raw: list[dict] = []
    for s in segs:
        wlist = []
        for w in (getattr(s, "words", None) or []):
            wlist.append({"word": w.word, "start": w.start, "end": w.end})
        raw.append({"start": s.start, "end": s.end, "text": s.text, "words": wlist})
    out = normalize_segments(raw)
    lang = getattr(info, "language", None) or language or "en"
    out["language"] = lang
    info_duration = getattr(info, "duration", None)
    try:
        if info_duration is not None and float(info_duration) > float(out.get("duration", 0.0)):
            out["duration"] = float(info_duration)
    except (TypeError, ValueError):
        pass
    return out
