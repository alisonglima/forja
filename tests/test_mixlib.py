import numpy as np


def test_duck_envelope_has_one_sample_per_sample_rate():
    from forja import mixlib

    env = mixlib.duck_envelope(2.0, 100, [], 0.2)
    assert isinstance(env, np.ndarray) and env.shape == (200,), "envelope deve ter total_s*sr amostras"


def test_duck_envelope_is_unity_outside_intervals():
    from forja import mixlib

    env = mixlib.duck_envelope(2.0, 100, [(0.5, 1.5, 0.25)], 0.1)
    assert np.isclose(env[0], 1.0) and np.isclose(env[-1], 1.0), "fora das janelas o ganho deve ser 1.0"


def test_duck_envelope_applies_interval_gain_on_plateau():
    from forja import mixlib

    env = mixlib.duck_envelope(2.0, 100, [(0.5, 1.5, 0.25)], 0.2)
    assert np.isclose(env[100], 0.25), "no miolo da janela o ganho deve ser o ganho pedido"


def test_duck_envelope_ramps_down_smoothly_at_interval_start():
    from forja import mixlib

    env = mixlib.duck_envelope(2.0, 100, [(0.5, 1.5, 0.25)], 0.2)
    assert np.all(np.diff(env[50:70]) <= 1e-9), "a entrada deve descer sem degraus durante a rampa"


def test_duck_envelope_overlap_uses_smallest_gain():
    from forja import mixlib

    env = mixlib.duck_envelope(2.5, 100, [(0.5, 2.0, 0.5), (0.75, 1.25, 0.2)], 0.05)
    assert np.isclose(env[100], 0.2), "sobreposição deve usar o menor ganho, não a soma"


def test_duck_envelope_without_intervals_is_all_ones():
    from forja import mixlib

    env = mixlib.duck_envelope(1.5, 80, [], 0.3)
    assert np.allclose(env, 1.0), "sem janelas o envelope deve ser constante em 1.0"


def test_duck_envelope_never_exceeds_unity_for_attenuation_gains():
    from forja import mixlib

    env = mixlib.duck_envelope(2.0, 100, [(0.2, 0.8, 0.5), (1.0, 1.8, 0.2)], 0.1)
    assert env.min() >= 0.0 and env.max() <= 1.0, "ganhos de ducking devem ficar em [0, 1]"


def test_db_to_gain_converts_known_decibel_values():
    from forja import mixlib

    gains = [mixlib.db_to_gain(0.0), mixlib.db_to_gain(-6.020599913), mixlib.db_to_gain(6.020599913)]
    assert np.allclose(gains, [1.0, 0.5, 2.0]), "0 dB -> 1, -6.02 dB -> 0.5, +6.02 dB -> 2"


def test_loudnorm_measure_cmd_asks_ffmpeg_for_json():
    from forja import mixlib

    cmd = mixlib.loudnorm_measure_cmd("in.wav", -16.0, -1.5, 11.0)
    joined = " ".join(cmd)
    assert (
        isinstance(cmd, list)
        and all(isinstance(arg, str) for arg in cmd)
        and "loudnorm" in joined
        and "I=-16.0" in joined
        and "TP=-1.5" in joined
        and "LRA=11.0" in joined
        and "print_format=json" in joined
        and "in.wav" in joined
    ), "medicao deve pedir loudnorm com I/TP/LRA e JSON no stderr"


def test_loudnorm_apply_cmd_uses_linear_two_pass_measurements():
    from forja import mixlib

    measured = {
        "input_i": "-18.2",
        "input_tp": "-2.1",
        "input_lra": "9.0",
        "input_thresh": "-28.5",
        "target_offset": "0.1",
        "I": "-18.2",
        "TP": "-2.1",
        "LRA": "9.0",
        "thresh": "-28.5",
        "offset": "0.1",
    }
    cmd = mixlib.loudnorm_apply_cmd("in.wav", "out.wav", -16.0, -1.5, 11.0, measured)
    joined = " ".join(cmd)
    assert (
        "linear=true" in joined
        and joined.count("measured_") >= 3
        and "in.wav" in joined
        and "out.wav" in joined
        and ":offset=0.1" in joined
        and "measured_offset" not in joined
        and cmd[1] == "-y"
    ), "segundo passe: linear=true, valores medidos, opcao `offset` (nao measured_offset) e -y"


def test_parse_loudnorm_json_reads_block_at_end_of_stderr():
    from forja import mixlib

    stderr = 'frame=1 fps=0\n{\n  "input_i": "-18.2",\n  "input_tp": "-2.1"\n}\n'
    parsed = mixlib.parse_loudnorm_json(stderr)
    assert parsed == {"input_i": "-18.2", "input_tp": "-2.1"}, "deve extrair o objeto JSON final do stderr"


def test_voice_gain_cmd_uses_one_pass_loudnorm_with_fixed_limits():
    from forja import mixlib

    cmd = mixlib.voice_gain_cmd("voz.wav", "voz_norm.wav", -18.0)
    joined = " ".join(cmd)
    assert (
        "loudnorm" in joined
        and "I=-18.0" in joined
        and "TP=-1.5" in joined
        and "LRA=7" in joined
        and "voz_norm.wav" in joined
        and cmd[1] == "-y"
    ), "ganho de voz deve ser loudnorm de 1 passe com TP=-1.5 e LRA=7 e sobrescrever a saida"


def test_loudnorm_measure_cmd_rejects_filter_injection():
    import pytest

    from forja import mixlib

    with pytest.raises(ValueError):
        mixlib.loudnorm_measure_cmd("in.wav", "0:foo", -1.5, 11.0)


def test_voice_gain_cmd_rejects_filter_injection():
    import pytest

    from forja import mixlib

    with pytest.raises(ValueError):
        mixlib.voice_gain_cmd("voz.wav", "out.wav", "0:foo")


def test_loudnorm_apply_cmd_rejects_non_numeric_measurement():
    import pytest

    from forja import mixlib

    measured = {
        "measured_I": "0:foo",
        "measured_TP": -1.5,
        "measured_LRA": 7.0,
        "measured_thresh": -20.0,
        "measured_offset": 0.0,
    }
    with pytest.raises(ValueError):
        mixlib.loudnorm_apply_cmd("in.wav", "out.wav", -16.0, -1.5, 11.0, measured)
