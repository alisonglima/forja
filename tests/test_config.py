"""Contratos de forja.config descritos no DESIGN.md."""
import copy

import pytest
import yaml


def _write(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_has_documented_sections():
    from forja import config

    assert {"project", "input", "transcribe", "voices", "mix", "render", "qa"} <= set(
        config.DEFAULTS
    )


def test_defaults_has_documented_scalar_values():
    from forja import config

    assert (
        config.DEFAULTS["voices"]["min_tempo"],
        config.DEFAULTS["voices"]["max_tempo"],
        config.DEFAULTS["mix"]["voice_lufs"],
        config.DEFAULTS["render"]["cps_max"],
        config.DEFAULTS["qa"]["max_wer"],
    ) == (0.90, 1.20, -18.0, 20.0, 0.15)


def test_config_error_is_a_value_error():
    from forja import config

    assert issubclass(config.ConfigError, ValueError)


def test_load_config_merges_empty_mapping_over_defaults(tmp_path):
    from forja import config

    path = _write(tmp_path, "{}\n")
    assert config.load_config(path) == config.DEFAULTS


def test_load_config_deep_merges_nested_sections(tmp_path):
    from forja import config

    path = _write(tmp_path, "voices:\n  provider: mock\n")
    loaded = config.load_config(path)
    assert loaded["voices"]["provider"] == "mock"
    assert loaded["voices"]["max_tempo"] == 1.20


def test_load_config_keeps_default_siblings_of_overridden_key(tmp_path):
    from forja import config

    path = _write(tmp_path, "render:\n  fps: 24\n")
    loaded = config.load_config(path)
    assert loaded["render"]["fps"] == 24
    assert loaded["render"]["width"] == 1280


def test_load_config_preserves_null_duration(tmp_path):
    from forja import config

    path = _write(tmp_path, "input:\n  duration: null\n")
    assert config.load_config(path)["input"]["duration"] is None


def test_load_config_rejects_inverted_tempo(tmp_path):
    from forja import config

    path = _write(tmp_path, "voices:\n  min_tempo: 1.5\n  max_tempo: 1.2\n")
    with pytest.raises(config.ConfigError) as excinfo:
        config.load_config(path)
    assert "min_tempo" in str(excinfo.value)


def test_load_config_accepts_equal_tempo_boundary(tmp_path):
    from forja import config

    path = _write(tmp_path, "voices:\n  min_tempo: 1.2\n  max_tempo: 1.2\n")
    loaded = config.load_config(path)
    assert loaded["voices"]["min_tempo"] == loaded["voices"]["max_tempo"] == 1.2


def test_load_config_rejects_nonpositive_fps(tmp_path):
    from forja import config

    path = _write(tmp_path, "render:\n  fps: 0\n")
    with pytest.raises(config.ConfigError) as excinfo:
        config.load_config(path)
    assert "fps" in str(excinfo.value)


def test_load_config_rejects_unknown_provider(tmp_path):
    from forja import config

    path = _write(tmp_path, "voices:\n  provider: elevenlabs\n")
    with pytest.raises(config.ConfigError) as excinfo:
        config.load_config(path)
    assert "provider" in str(excinfo.value)


def test_load_config_rejects_positive_true_peak(tmp_path):
    from forja import config

    path = _write(tmp_path, "mix:\n  true_peak: 0.5\n")
    with pytest.raises(config.ConfigError) as excinfo:
        config.load_config(path)
    assert "true_peak" in str(excinfo.value)


def test_load_config_accepts_zero_true_peak_boundary(tmp_path):
    from forja import config

    path = _write(tmp_path, "mix:\n  true_peak: 0.0\n")
    assert config.load_config(path)["mix"]["true_peak"] == 0.0


def test_write_default_config_writes_the_defaults(tmp_path):
    from forja import config

    path = tmp_path / "config.yaml"
    config.write_default_config(path)
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == config.DEFAULTS


def test_write_default_config_applies_section_overrides(tmp_path):
    from forja import config

    path = tmp_path / "config.yaml"
    config.write_default_config(path, mix={"target_lufs": -14.0})
    written = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert written["mix"]["target_lufs"] == -14.0
    assert written["render"] == config.DEFAULTS["render"]


def test_write_default_config_refuses_to_overwrite(tmp_path):
    from forja import config

    path = tmp_path / "config.yaml"
    path.write_text("sentinel: true\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        config.write_default_config(path, project={"name": "outro"})
    assert path.read_text(encoding="utf-8") == "sentinel: true\n"


def test_load_config_does_not_mutate_defaults(tmp_path):
    from forja import config

    before = copy.deepcopy(config.DEFAULTS)
    path = _write(tmp_path, "voices:\n  provider: mock\n")
    config.load_config(path)
    assert config.DEFAULTS == before


def test_load_config_rejects_filter_injection_in_mix(tmp_path):
    from forja import config

    path = _write(tmp_path, "mix:\n  target_lufs: '0:foo'\n")
    with pytest.raises(config.ConfigError) as excinfo:
        config.load_config(path)
    assert "target_lufs" in str(excinfo.value)


def test_load_config_rejects_non_numeric_render_font_size(tmp_path):
    from forja import config

    path = _write(tmp_path, "render:\n  font_size: '32:foo'\n")
    with pytest.raises(config.ConfigError) as excinfo:
        config.load_config(path)
    assert "font_size" in str(excinfo.value)


def test_load_config_rejects_out_of_range_mix(tmp_path):
    from forja import config

    path = _write(tmp_path, "mix:\n  lra: 500\n")
    with pytest.raises(config.ConfigError) as excinfo:
        config.load_config(path)
    assert "lra" in str(excinfo.value)


def test_default_voice_provider_is_files():
    from forja import config

    assert config.DEFAULTS["voices"]["provider"] == "files"
    assert config.DEFAULTS["voices"]["input_dir"] == "voices"


def test_load_config_rejects_voice_input_dir_escape(tmp_path):
    from forja import config

    path = _write(tmp_path, "voices:\n  input_dir: ../fora\n")
    with pytest.raises(config.ConfigError) as excinfo:
        config.load_config(path)
    assert "input_dir" in str(excinfo.value)


def test_load_config_accepts_a_registered_tts_provider(tmp_path):
    from forja import config, registry

    registry.reset_for_tests()
    try:
        registry.register("tts", "custom-test")(lambda: None)
        path = _write(tmp_path, "voices:\n  provider: custom-test\n")
        assert config.load_config(path)["voices"]["provider"] == "custom-test"
    finally:
        registry.reset_for_tests()


def test_default_brand_theme_is_documented():
    from forja import config

    brand = config.DEFAULTS["brand"]
    assert brand["primary"].startswith("#") and brand["font"]
    assert brand["safe_margin"] >= 0


def test_load_config_rejects_bad_brand_color(tmp_path):
    from forja import config

    path = _write(tmp_path, "brand:\n  primary: vermelho\n")
    with pytest.raises(config.ConfigError) as excinfo:
        config.load_config(path)
    assert "brand.primary" in str(excinfo.value)


def test_load_config_rejects_brand_logo_escape(tmp_path):
    from forja import config

    path = _write(tmp_path, "brand:\n  logo: ../fora.png\n")
    with pytest.raises(config.ConfigError) as excinfo:
        config.load_config(path)
    assert "brand.logo" in str(excinfo.value)


def test_load_config_accepts_piper_with_defaults(tmp_path):
    from forja import config

    path = _write(tmp_path, "voices:\n  provider: piper\n")
    loaded = config.load_config(path)
    assert loaded["voices"]["provider"] == "piper"
    assert loaded["voices"]["piper"]["model"].endswith(".onnx")


def test_load_config_rejects_piper_bad_length_scale(tmp_path):
    from forja import config

    path = _write(tmp_path, "voices:\n  provider: piper\n  piper:\n    length_scale: 3\n")
    with pytest.raises(config.ConfigError) as excinfo:
        config.load_config(path)
    assert "length_scale" in str(excinfo.value)
