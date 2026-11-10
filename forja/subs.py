from __future__ import annotations

# Legendas: monta eventos a partir do schedule e exporta SRT.
# Helper local de quebra de linhas; sera unificado com cues.py depois.

_PUNCT = (",", ";", ":", ".", "?", "!")
_MIN_DURATION = 0.8
_MARGIN = 0.2


def _wrap(words, max_chars, max_lines, prefer_punct):
    """Greedy word wrap; returns None when it does not fit."""
    lines = []
    remaining = list(words)
    while remaining:
        count = 0
        length = 0
        while count < len(remaining):
            word = remaining[count]
            add = len(word) + (1 if count else 0)
            if length + add > max_chars:
                break
            length += add
            count += 1
        if count == 0:
            return None
        if prefer_punct and count < len(remaining):
            for i in range(count - 1, -1, -1):
                if remaining[i].endswith(_PUNCT):
                    count = i + 1
                    break
        lines.append(" ".join(remaining[:count]))
        remaining = remaining[count:]
        if len(lines) > max_lines:
            return None
    return lines


def _split_lines(text, max_chars, max_lines):
    """Split text by words, preferring breaks after punctuation."""
    words = str(text).split()
    if not words:
        return []
    if max_chars < 1 or max_lines < 1:
        return None
    result = _wrap(words, max_chars, max_lines, True)
    if result is None:
        result = _wrap(words, max_chars, max_lines, False)
    return result


def _chunk_text(text, max_chars, max_lines):
    """Split text into chunks, each fitting in max_lines lines."""
    words = str(text).split()
    chunks = []
    current = []
    queue = list(words)
    while queue:
        word = queue.pop(0)
        if not current:
            current = [word]
            continue
        trial = current + [word]
        if _split_lines(" ".join(trial), max_chars, max_lines) is not None:
            current = trial
            continue
        cut = 0
        for i in range(len(current) - 1, -1, -1):
            if current[i].endswith(_PUNCT):
                cut = i + 1
                break
        if cut and cut < len(current):
            chunks.append(current[:cut])
            current = current[cut:]
            queue.insert(0, word)
        else:
            chunks.append(current)
            current = [word]
    if current:
        chunks.append(current)
    return chunks


def _raised(start, end, lower_thirds):
    for window in lower_thirds or []:
        try:
            lo = float(window[0])
            hi = float(window[1])
        except (TypeError, ValueError, IndexError):
            continue
        if start <= hi + _MARGIN and end >= lo - _MARGIN:
            return True
    return False


def _cue_events(entry, cue, cfg, next_start):
    render = cfg.get("render", {})
    max_chars = int(render.get("max_chars_line", 42))
    max_lines = int(render.get("max_lines", 2))

    start = float(entry.get("start", 0.0))
    end = float(entry.get("end", start))
    if next_start is not None:
        end = min(end, next_start)
    if end < start:
        end = start

    chunks = _chunk_text(cue.get("text", ""), max_chars, max_lines)
    if not chunks:
        chunks = [[""]]
    texts = [" ".join(chunk) for chunk in chunks]
    total_chars = sum(len(text) for text in texts) or 1
    span = end - start
    narrador = cue.get("role") == "narrator"

    events = []
    consumed = 0
    for text in texts:
        event_start = start + span * consumed / total_chars
        consumed += len(text)
        event_end = start + span * consumed / total_chars
        lines = _split_lines(text, max_chars, max_lines)
        if lines is None:
            lines = [text]
        events.append({
            "start": event_start,
            "end": event_end,
            "lines": lines,
            "narrador": narrador,
            "raised": False,
        })
    return events


def build_subs(schedule, cues, lower_thirds, cfg):
    """Build subtitle events from a schedule and cues."""
    entries = sorted(
        schedule.get("cues", []),
        key=lambda entry: float(entry.get("start", 0.0)),
    )
    by_id = {cue.get("id"): cue for cue in cues or []}
    total = float(schedule.get("total", 0.0))

    events = []
    for i, entry in enumerate(entries):
        cue = by_id.get(entry.get("id"))
        if cue is None:
            continue
        next_start = None
        if i + 1 < len(entries):
            next_start = float(entries[i + 1].get("start", 0.0))
        events.extend(_cue_events(entry, cue, cfg, next_start))

    for i, event in enumerate(events):
        if i + 1 < len(events):
            boundary = events[i + 1]["start"]
        elif total > event["start"]:
            boundary = total
        else:
            boundary = None

        if boundary is not None and event["end"] > boundary:
            event["end"] = boundary
        if event["end"] < event["start"]:
            event["end"] = event["start"]

        if event["end"] - event["start"] < _MIN_DURATION:
            limit = boundary if boundary is not None else event["start"] + _MIN_DURATION
            event["end"] = max(
                event["end"],
                min(event["start"] + _MIN_DURATION, limit),
            )

        event["raised"] = _raised(event["start"], event["end"], lower_thirds)

    return events


def _timecode(seconds):
    ms = int(round(float(seconds) * 1000))
    if ms < 0:
        ms = 0
    hours, rem = divmod(ms, 3600000)
    minutes, rem = divmod(rem, 60000)
    secs, ms = divmod(rem, 1000)
    return "%02d:%02d:%02d,%03d" % (hours, minutes, secs, ms)


def to_srt(subs):
    """Render subtitle events as SRT."""
    blocks = []
    for index, sub in enumerate(subs or [], 1):
        lines = sub.get("lines") or [""]
        blocks.append(
            "%d\n%s --> %s\n%s"
            % (
                index,
                _timecode(sub.get("start", 0.0)),
                _timecode(sub.get("end", 0.0)),
                "\n".join(lines),
            )
        )
    if not blocks:
        return ""
    return "\n\n".join(blocks) + "\n"
