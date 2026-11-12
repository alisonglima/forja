"""Contrato de `forja/render.py` para video vertical (T-VID-RENDER-01).

plano:2637: `build_props` aceita `brand` injetado, nao muta o default,
`remotion_cmd`/`mux_cmd` estaveis e props de story em 1080x1920/30 fps.
plano:1574/1617: o runtime de marca preenche `brand`; `forja/render.py` aceita
override de `brand`, nao do default. DESIGN.md:135-137 fixa as assinaturas e o
argv do mux (`-c:v copy`, AAC 192k, `-shortest`, `-movflags +faststart`);
DESIGN.md:163-172 fixa as chaves dos props lidas via `--props`.
"""
# LACUNA: nome do parametro de override e sentido de `brand=None` nao decididos;
# este teste usa `brand=` e assume None = herdar o `brand` da config.
# LACUNA: 1080x1920/30 nao e declarado como default; o teste exige pass-through.
import copy


def _brand():
    return {"primary": "#00338D", "ink": "#0d2240", "paper": "#ffffff",
            "accent": "#00AB68", "font": "Roboto", "safe_margin": 48}


def _cfg(brand=None):
    cfg = {"render": {"width": 1080, "height": 1920, "fps": 30, "font_size": 32}}
    return {**cfg, **({"brand": brand} if brand is not None else {})}


def test_build_props_carries_story_size_and_30_fps():
    from forja import render

    props = render.build_props("clip.mp4", 5.0, [], [], _cfg())
    assert (props["width"], props["height"], props["fps"]) == (1080, 1920, 30)


def test_build_props_uses_config_brand_when_not_overridden():
    from forja import render

    brand = _brand()
    assert render.build_props("clip.mp4", 5.0, [], [], _cfg(brand))["brand"] == brand


def test_build_props_injected_brand_overrides_config_brand():
    from forja import render

    override = {**_brand(), "accent": "#00338D", "font": "Helvetica"}
    props = render.build_props("clip.mp4", 5.0, [], [], _cfg(_brand()), brand=override)
    assert props["brand"] == override


def test_build_props_does_not_mutate_config_or_injected_brand():
    from forja import render

    cfg, override = _cfg(_brand()), _brand()
    before = copy.deepcopy((cfg, override))
    props = render.build_props("clip.mp4", 5.0, [], [], cfg, brand=override)
    props["brand"]["accent"] = "#FFFFFF"
    assert (cfg, override) == before


def test_build_props_default_brand_is_fresh_and_empty():
    from forja import render

    first = render.build_props("clip.mp4", 0.0, [], [], _cfg())
    first["brand"]["accent"] = "#FFFFFF"
    second = render.build_props("clip.mp4", 0.0, [], [], _cfg())
    assert (second["brand"], second["subs"], second["lowerThirds"]) == ({}, [], [])


def test_remotion_cmd_is_stable():
    from forja import render

    assert render.remotion_cmd("src/index.jsx", "props.json", "work", "out/render.mp4") == [
        "remotion", "render", "src/index.jsx", "Legendas", "out/render.mp4",
        "--props", "props.json", "--public-dir", "work",
    ]


def test_remotion_cmd_storyboard_composition_is_stable():
    from forja import render

    expected = ["remotion", "render", "src/index.jsx", "Storyboard", "out/render.mp4",
                "--props", "props.json", "--public-dir", "work"]
    got = render.remotion_cmd("src/index.jsx", "props.json", "work", "out/render.mp4",
                              composition="Storyboard")
    assert got == expected


def test_mux_cmd_is_stable():
    from forja import render

    assert render.mux_cmd("video.mp4", "mix.wav", "final.mp4") == [
        "ffmpeg", "-y", "-i", "video.mp4", "-i", "mix.wav", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
        "final.mp4",
    ]
