import copy


def _raw():
    return [
        {
            "start": 0.0,
            "end": 1.2,
            "text": " Hello  world ",
            "words": [
                {"word": " Hello", "start": 0.0, "end": 0.5},
                {"word": "world ", "start": 0.5, "end": 1.2},
            ],
        },
        {"start": 1.5, "end": 2.0, "text": "Again", "words": []},
    ]


def test_normalize_segments_returns_contract_keys():
    from forja import transcribe

    out = transcribe.normalize_segments(_raw())
    assert set(out) == {"language", "duration", "segments"}, "saida deve ter language, duration e segments"


def test_normalize_segments_strips_segment_text():
    from forja import transcribe

    out = transcribe.normalize_segments(_raw())
    text = out["segments"][0]["text"]
    assert text == text.strip() and text.startswith("Hello"), "texto do segmento nao deve ter espacos nas pontas"


def test_normalize_segments_discards_empty_segments():
    from forja import transcribe

    raw = _raw() + [{"start": 2.1, "end": 2.2, "text": "   ", "words": []}]
    out = transcribe.normalize_segments(raw)
    assert len(out["segments"]) == 2, "segmentos vazios ou so com espacos devem ser descartados"


def test_normalize_segments_guarantees_start_not_after_end():
    from forja import transcribe

    out = transcribe.normalize_segments([{"start": 2.0, "end": 1.0, "text": "invertido", "words": []}])
    segment = out["segments"][0]
    assert segment["start"] <= segment["end"], "start nunca pode ser maior que end"


def test_normalize_segments_strips_word_text():
    from forja import transcribe

    out = transcribe.normalize_segments(_raw())
    words = [word["word"] for word in out["segments"][0]["words"]]
    assert words == [word.strip() for word in words], "cada palavra deve vir sem espacos nas pontas"


def test_normalize_segments_preserves_word_timing():
    from forja import transcribe

    out = transcribe.normalize_segments(_raw())
    word = out["segments"][0]["words"][0]
    assert word["start"] == 0.0 and word["end"] == 0.5, "tempos das palavras devem ser preservados"


def test_normalize_segments_duration_covers_last_segment():
    from forja import transcribe

    out = transcribe.normalize_segments(_raw())
    last_end = max(segment["end"] for segment in out["segments"])
    assert out["duration"] >= last_end, "duracao total deve cobrir o fim do ultimo segmento"


def test_normalize_segments_empty_input_yields_no_segments():
    from forja import transcribe

    out = transcribe.normalize_segments([])
    assert out["segments"] == [], "lista vazia deve virar segments vazio"


def test_normalize_segments_missing_words_becomes_empty_list():
    from forja import transcribe

    out = transcribe.normalize_segments([{"start": 0.0, "end": 1.0, "text": "sem palavras"}])
    assert out["segments"][0]["words"] == [], "segmento sem words deve virar lista vazia"


def test_normalize_segments_preserves_segment_order():
    from forja import transcribe

    out = transcribe.normalize_segments(_raw())
    starts = [segment["start"] for segment in out["segments"]]
    assert starts == sorted(starts), "segmentos devem manter a ordem cronologica de entrada"


def test_normalize_segments_language_is_a_string():
    from forja import transcribe

    out = transcribe.normalize_segments(_raw())
    assert isinstance(out["language"], str) and out["language"], "language deve ser uma string nao vazia"


def test_normalize_segments_does_not_mutate_raw_input():
    from forja import transcribe

    raw = _raw()
    before = copy.deepcopy(raw)
    transcribe.normalize_segments(raw)
    assert raw == before, "normalize_segments nao deve alterar a lista recebida"
