import copy
import json


def _cfg():
    return {
        "render": {
            "width": 1280,
            "height": 720,
            "fps": 30,
            "font_size": 32,
            "max_chars_line": 42,
            "max_lines": 2,
            "cps_max": 20.0,
        }
    }


def _subs():
    return [
        {"start": 0.5, "end": 2.0, "lines": ["Ola mundo"], "narrador": False, "raised": False},
        {"start": 2.2, "end": 3.0, "lines": ["Ate logo"], "narrador": True, "raised": True},
    ]


def _contains(value, target):
    if value == target:
        return True
    if isinstance(value, dict):
        return any(_contains(item, target) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains(item, target) for item in value)
    return False


def test_build_props_returns_json_serializable_dict():
    from forja import render

    props = render.build_props("clip.mp4", 5.0, _subs(), [[1.0, 1.5]], _cfg())
    assert isinstance(props, dict) and json.dumps(props), "props deve ser um dict serializavel para o Remotion"


def test_build_props_includes_clip_name_and_total_duration():
    from forja import render

    props = render.build_props("meu-clip.mp4", 12.5, _subs(), [], _cfg())
    assert _contains(props, "meu-clip.mp4") and _contains(props, 12.5), "props deve levar clip e duracao total"


def test_build_props_includes_subtitle_events():
    from forja import render

    subs = _subs()
    props = render.build_props("clip.mp4", 5.0, subs, [], _cfg())
    assert _contains(props, subs), "props deve levar os eventos de legenda para o template"


def test_build_props_includes_lower_third_windows():
    from forja import render

    lower = [[1.0, 1.5]]
    props = render.build_props("clip.mp4", 5.0, _subs(), lower, _cfg())
    assert _contains(props, lower), "props deve levar as janelas de tarja para o template"


def test_build_props_accepts_empty_subs_and_lower_thirds():
    from forja import render

    props = render.build_props("clip.mp4", 0.0, [], [], _cfg())
    assert isinstance(props, dict) and json.dumps(props), "listas vazias nao podem quebrar a montagem dos props"


def test_build_props_does_not_mutate_its_inputs():
    from forja import render

    subs = _subs()
    lower = [[1.0, 1.5]]
    cfg = _cfg()
    before = copy.deepcopy((subs, lower, cfg))
    render.build_props("clip.mp4", 5.0, subs, lower, cfg)
    assert (subs, lower, cfg) == before, "build_props nao deve alterar as estruturas recebidas"


def test_remotion_cmd_returns_argv_with_entry_props_public_dir_and_out():
    from forja import render

    cmd = render.remotion_cmd("src/index.jsx", "props.json", "public", "out/video.mp4")
    joined = " ".join(cmd)
    assert (
        isinstance(cmd, list)
        and all(isinstance(arg, str) for arg in cmd)
        and "remotion" in joined
        and "src/index.jsx" in joined
        and "props.json" in joined
        and "public" in joined
        and "out/video.mp4" in joined
    ), "comando Remotion deve ser argv com entry, props, public_dir e saida"


def test_mux_cmd_copies_video_and_encodes_aac_192k():
    from forja import render

    cmd = render.mux_cmd("video.mp4", "mix.wav", "final.mp4")
    joined = " ".join(cmd)
    assert (
        "ffmpeg" in joined
        and "-c:v copy" in joined
        and "-c:a aac" in joined
        and "-b:a 192k" in joined
        and "-shortest" in joined
        and "video.mp4" in joined
        and "mix.wav" in joined
        and "final.mp4" in joined
    ), "mux deve copiar o video e codificar AAC 192k terminando no menor stream"


def test_mux_cmd_adds_faststart_for_streaming():
    from forja import render

    cmd = render.mux_cmd("video.mp4", "mix.wav", "final.mp4")
    joined = " ".join(cmd)
    assert "-movflags" in joined and "+faststart" in joined, "mp4 final deve ter -movflags +faststart"


def test_remotion_cmd_defaults_to_legendas_composition():
    from forja import render

    cmd = render.remotion_cmd("src/index.jsx", "p.json", "pub", "out.mp4")
    assert cmd[3] == "Legendas"


def test_remotion_cmd_accepts_another_composition():
    from forja import render

    cmd = render.remotion_cmd("src/index.jsx", "p.json", "pub", "out.mp4", composition="Storyboard")
    assert cmd[3] == "Storyboard" and cmd[2] == "src/index.jsx" and cmd[4] == "out.mp4"
