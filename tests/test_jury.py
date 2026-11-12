"""Contrato `forja.jury.score` (L-T-JM-01 congela N-25, plano:849).
Contrato (plano:750; plano:777; §4.7): 5 criterios pesos 20/25/20/20/15;
nota=soma(peso x nota)/5 (0-100); limiar 85/100 e nenhum criterio <3;
70-84,9 corrige (max 2 rodadas), <70 bloqueia; parte medida x editorial
(editorial nunca vira medida; nota alta nao troca gate humano); retorna
`medido`,`editorial`,`total`,`bloqueios`,`veredito`; abaixo do limiar ou
criterio <3 => `bloqueado`, nunca oculto.
# LACUNA: literais do veredito aprovado e do veredito de correcao.
# LACUNA: regra medida+editorial (aqui m==e; cruzados 1x5 bloqueiam).
# LACUNA: `passes` (plano:750 "uma vez" x §4.7 "duas rodadas"); formato
# de `bloqueios`/`medido`/`editorial`; criterio parcial; tipos errados;
# sem hostil de arquivo (score recebe dicts, nao le caminho/JSON).
"""

_CRITERIOS = (("vf", 20), ("hl", 25), ("mi", 20), ("fp", 20), ("pe", 15))


def _rubric():
    return {"criterios": [{"id": c, "peso": p} for c, p in _CRITERIOS], "limiar": 85, "minimo": 3}


def _notas(v):
    return dict(v) if isinstance(v, dict) else {c: v for c, _ in _CRITERIOS}


def _score(m, e, passes=1):
    from forja import jury

    return jury.score({"id": "p1"}, _rubric(), _notas(m), _notas(e), passes=passes)


def test_retorno_tem_as_cinco_chaves_e_aceita_passes_padrao():
    from forja import jury

    res = jury.score({"id": "p1"}, _rubric(), _notas(5), _notas(5))
    for chave in ("medido", "editorial", "total", "bloqueios", "veredito"):
        assert chave in res
    assert isinstance(res["veredito"], str)


def test_tudo_cinco_total_100_sem_bloqueios():
    res = _score(5, 5)
    assert res["total"] == 100.0
    assert res["bloqueios"] == []
    assert res["veredito"] != "bloqueado"


def test_total_ponderado_pelos_pesos_da_rubrica():
    res = _score(dict(_notas(5), pe=1), dict(_notas(5), pe=1))
    assert res["total"] == 88.0


def test_limiar_85_com_minimo_3_aprova():
    n = dict(_notas(4), vf=5, fp=5, pe=3)
    assert _score(n, n)["total"] == 85.0
    assert _score(n, n)["veredito"] != "bloqueado"


def test_faixa_80_corrige_na_primeira_passada():
    res = _score(4, 4, passes=1)
    assert res["total"] == 80.0
    assert res["veredito"] != "bloqueado"


def test_faixa_70_corrige_na_primeira_passada():
    n = dict(_notas(3), fp=4, pe=5)
    res = _score(n, n, passes=1)
    assert res["total"] == 70.0
    assert res["veredito"] != "bloqueado"


def test_abaixo_de_70_bloqueia_em_qualquer_passada():
    n = dict(_notas(3), fp=4, pe=4)
    for passes in (1, 2):
        res = _score(n, n, passes=passes)
        assert res["total"] == 67.0
        assert res["veredito"] == "bloqueado"
        assert isinstance(res["bloqueios"], list) and res["bloqueios"]


def test_criterio_abaixo_de_3_bloqueia_mesmo_com_total_alto():
    n = dict(_notas(5), pe=2)
    res = _score(n, n)
    assert res["total"] == 91.0
    assert res["veredito"] == "bloqueado"
    assert isinstance(res["bloqueios"], list) and res["bloqueios"]


def test_nota_editorial_alta_nao_cobre_falha_medida():
    assert _score(1, 5)["veredito"] == "bloqueado"


def test_falha_editorial_tambem_bloqueia():
    assert _score(5, 1)["veredito"] == "bloqueado"


def test_medido_e_editorial_nao_se_misturam():
    cheio = _score(5, 5)
    assert _score(5, 1)["medido"] == cheio["medido"]
    assert _score(1, 5)["editorial"] == cheio["editorial"]


def test_nunca_ha_aprovado_com_ressalvas():
    n = dict(_notas(5), pe=2)
    for res in (_score(5, 5), _score(4, 4, passes=1), _score(4, 4, passes=3),
                _score(1, 1), _score(n, n)):
        assert res["veredito"] != "aprovado com ressalvas"


def test_faixa_sem_nova_nota_bloqueia_na_terceira_passada():
    res = _score(4, 4, passes=3)
    assert res["total"] == 80.0
    assert res["veredito"] == "bloqueado"


def test_entrada_vazia_bloqueia_fechado():
    from forja import jury

    res = jury.score({"id": "p1"}, _rubric(), {}, {})
    assert res["veredito"] == "bloqueado"
    assert isinstance(res["bloqueios"], list) and res["bloqueios"]


def test_mesma_entrada_mesmo_resultado():
    assert _score(4, 4) == _score(4, 4)
