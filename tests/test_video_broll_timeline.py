"""Contrato T-VID-BROLL-01B: timeline do b-roll (ordem, duracao, corte, legenda).
Congela L-VID-BROLL-01 (plano:2607) so nesta fatia: valida 9:16/1080p fica em
01A; aqui so timeline a partir de copy.json roteiro_video (plano:2924: gancho,
3 pontos, CTA, duracao) + assets ingeridos do Flow (plano:2571, plano:2647).
API minima congelada: broll.build_timeline(segmentos, assets) e broll.to_srt.
LACUNA: plano nao nomeia funcao/assinatura; nomes acima sao o congelamento.
"""
import pytest


def _segs():
    return [
        {"id": "gancho", "asset": "a1", "duracao_s": 2.0, "texto": "Olhe aqui"},
        {"id": "p1", "asset": "a2", "duracao_s": 3.0, "texto": "Primeiro ponto"},
        {"id": "cta", "asset": "a3", "duracao_s": 2.0, "texto": "Fale conosco"},
    ]


def _assets():
    return {"a1": {"duration": 10.0}, "a2": {"duration": 10.0}, "a3": {"duration": 10.0}}


def test_build_timeline_preserva_ordem_e_contiguidade(tmp_path):
    from forja import broll

    tl = broll.build_timeline(_segs(), _assets())
    assert [s["id"] for s in tl["segments"]] == ["gancho", "p1", "cta"]
    assert [(s["start"], s["end"]) for s in tl["segments"]] == [(0.0, 2.0), (2.0, 5.0), (5.0, 7.0)]


def test_build_timeline_total_e_a_soma_das_duracoes(tmp_path):
    from forja import broll

    tl = broll.build_timeline(_segs(), _assets())
    assert tl["total_s"] == 7.0


def test_build_timeline_aplica_corte_dentro_do_asset(tmp_path):
    from forja import broll

    segs = [{"id": "p1", "asset": "a1", "duracao_s": 3.0, "texto": "Corte", "corte": {"in": 1.0, "out": 4.0}}]
    tl = broll.build_timeline(segs, {"a1": {"duration": 10.0}})
    seg = tl["segments"][0]
    assert (seg["start"], seg["end"]) == (0.0, 3.0)
    assert (seg["cut_in"], seg["cut_out"]) == (1.0, 4.0)


def test_build_timeline_rejeita_corte_fora_do_asset(tmp_path):
    from forja import broll
    from forja.errors import ForjaError

    segs = [{"id": "p1", "asset": "a1", "duracao_s": 3.0, "texto": "X", "corte": {"in": 8.0, "out": 99.0}}]
    with pytest.raises(ForjaError) as exc:
        broll.build_timeline(segs, {"a1": {"duration": 10.0}})
    assert exc.value.code == "CONFIG_INVALID"


def test_to_srt_emite_um_bloco_por_segmento_em_ordem(tmp_path):
    from forja import broll

    srt = broll.to_srt(broll.build_timeline(_segs(), _assets()))
    assert "1\n00:00:00,000 --> 00:00:02,000" in srt
    assert srt.count("-->") == 3
    assert srt.index("Olhe aqui") < srt.index("Primeiro ponto") < srt.index("Fale conosco")


def test_build_timeline_rejeita_segmentos_vazios(tmp_path):
    from forja import broll
    from forja.errors import ForjaError

    with pytest.raises(ForjaError) as exc:
        broll.build_timeline([], _assets())
    assert exc.value.code == "CONFIG_INVALID"


def test_build_timeline_rejeita_asset_ausente(tmp_path):
    from forja import broll
    from forja.errors import ForjaError

    with pytest.raises(ForjaError) as exc:
        broll.build_timeline(_segs(), {"a1": {"duration": 10.0}})
    assert exc.value.code == "MISSING_INPUT"


def test_build_timeline_rejeita_caminho_com_dotdot(tmp_path):
    from forja import broll
    from forja.errors import ForjaError

    segs = [{"id": "gancho", "asset": "../fora", "duracao_s": 2.0, "texto": "X"}]
    with pytest.raises(ForjaError) as exc:
        broll.build_timeline(segs, {"../fora": {"duration": 10.0}})
    assert exc.value.code == "CONFIG_INVALID"


def test_build_timeline_rejeita_tipo_errado_e_json_truncado(tmp_path):
    from forja import broll
    from forja.errors import ForjaError

    with pytest.raises(ForjaError) as exc:
        broll.build_timeline({"id": "gancho"}, _assets())
    assert exc.value.code == "CONFIG_INVALID"
    with pytest.raises(ForjaError) as exc2:
        broll.build_timeline([{"id": "gancho", "asset": "a1", "duracao_s": "dois", "texto": "X"}], _assets())
    assert exc2.value.code == "CONFIG_INVALID"
    # LACUNA: plano nao fixa tolerancia de float; aqui duracoes sinteticas usam igualdade exata.
