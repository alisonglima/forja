"""Contrato do verificador de grafia LEO (`forja/grafia.py`, T-GRAFIA-01).

Congela `grafia.check_text(texto, idioma="pt-BR", brand_root=None)`.
O `from forja import grafia` fica DENTRO de cada teste para que o
`--collect-only` passe sem a implementacao.
"""
import json


def test_ok_leo_clube_expandido():
    from forja import grafia
    assert grafia.check_text("O LEO Clube de Taquaritinga abre inscrições.") == []


def test_ok_leos_e_leoismo_maiusculos():
    from forja import grafia
    assert grafia.check_text("Os LEOs participaram do Dia Nacional do LEOísmo.") == []


def test_erro_leo_minusculo():
    from forja import grafia
    got = [(i["level"], i["code"], i["trecho"]) for i in grafia.check_text("O Leo Clube abre inscrições.")]
    assert got == [("error", "GRAFIA_LEO", "Leo")]


def test_erro_leos_minusculo_e_acentuado():
    from forja import grafia
    got = [(i["level"], i["code"], i["trecho"]) for i in grafia.check_text("Os Leos participaram.")]
    assert got == [("error", "GRAFIA_LEO", "Leos")]
    got = [(i["level"], i["code"], i["trecho"]) for i in grafia.check_text("Os Léos")]
    assert got == [("error", "GRAFIA_LEO", "Léos")]


def test_erro_leos_caixa_alta():
    from forja import grafia
    got = [(i["level"], i["code"], i["trecho"]) for i in grafia.check_text("Os LEOS participaram.")]
    assert got == [("error", "GRAFIA_LEO_PLURAL", "LEOS")]


def test_erro_derivado_maiusculo():
    from forja import grafia
    got = [(i["level"], i["code"], i["trecho"]) for i in grafia.check_text("O Leoísmo reúne os clubes.")]
    assert got == [("error", "GRAFIA_LEO_DERIVADO", "Leoísmo")]


def test_aviso_derivado_minusculo_sem_error():
    from forja import grafia
    got = [(i["level"], i["code"], i["trecho"]) for i in grafia.check_text("o leoísmo cresce")]
    assert got == [("warn", "GRAFIA_LEO_DERIVADO", "leoísmo")]


def test_aviso_nome_composto():
    from forja import grafia
    for texto in ("Clube de LEOs", "Multidistrito LEO", "Dia Nacional do LEO"):
        got = [(i["level"], i["code"]) for i in grafia.check_text(texto)]
        assert got == [("warn", "GRAFIA_LEO_NOME")]
    assert grafia.check_text("Dia Nacional do LEOísmo") == []


def test_ok_palavras_e_sigla_sozinha():
    from forja import grafia
    assert grafia.check_text("Leopoldo e Leonardo") == []
    assert grafia.check_text("LEO") == []


def test_dois_erros_no_mesmo_texto():
    from forja import grafia
    got = [(i["level"], i["code"], i["trecho"]) for i in grafia.check_text("Os Leos e o Leoísmo")]
    assert got == [("error", "GRAFIA_LEO", "Leos"), ("error", "GRAFIA_LEO_DERIVADO", "Leoísmo")]


def test_idioma_en_nao_verifica():
    from forja import grafia
    assert grafia.check_text("Os Leos participaram.", idioma="en") == []


def test_apostrofo_curvo_normalizado():
    from forja import grafia
    got = [(i["level"], i["code"], i["trecho"]) for i in grafia.check_text("Os LEO’s")]
    assert got == [("error", "GRAFIA_LEO_PLURAL", "LEO's")]


def test_texto_nao_str_ou_vazio():
    from forja import grafia
    assert grafia.check_text("") == []
    assert grafia.check_text(None) == []
    assert grafia.check_text(123) == []


def test_brand_root_sintetico(tmp_path):
    from forja import grafia
    data = {"verificacao": {"reprova": [{"codigo": "X", "padrao": "(?<!\\w)foo(?!\\w)", "mensagem": "m"}], "avisa": []}}
    (tmp_path / "grafia.json").write_text(json.dumps(data), encoding="utf-8")
    got = [(i["level"], i["code"], i["trecho"]) for i in grafia.check_text("foo bar", brand_root=tmp_path)]
    assert got == [("error", "X", "foo")]
