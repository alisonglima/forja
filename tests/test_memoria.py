"""T-MEM-01: contrato da memoria de correcoes (congela L-MEM-01).
plano:2601 L-MEM-01 forja/memoria.py NOVO; plano:2633 T-MEM-01 collect-only.
plano:632 jsonl com antes/depois/motivo/quem/hash; 3x mesmo padrao gera
propostas/regra-<id>.md com evidencia e escopo; so entra no lint apos o dono.
LACUNA: "mesmo padrao"/"hash"/decisao sem formato (aqui `padrao`, sha256 com NUL,
`propostas/decisoes.jsonl`). plano:2925, plano:2530."""
import hashlib
import json
import pytest
def _args(p="cta-final", a="COMPRE AGORA", d="Garanta sua vaga"):
    return {"antes": a, "depois": d, "motivo": "tom agressivo", "por": "Ana", "padrao": p}
def _prop(t):
    from forja import memoria
    for _ in range(3):
        memoria.registrar_correcao(t, **_args())
    return t / "propostas" / "regra-cta-final.md"
def test_registra_correcao_com_antes_depois_motivo_quem_e_hash(tmp_path):
    from forja import memoria
    rec = memoria.registrar_correcao(tmp_path, **_args())
    dado = json.loads((tmp_path / "memoria-correcoes.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert dado["antes"] == "COMPRE AGORA" and dado["depois"] == "Garanta sua vaga"
    assert dado["motivo"] == "tom agressivo" and dado["por"] == "Ana"
    assert dado["hash"] == hashlib.sha256("COMPRE AGORA\x00Garanta sua vaga".encode()).hexdigest()
    assert rec == dado
def test_correcao_com_antes_vazio_falha(tmp_path):
    from forja import memoria
    from forja.errors import ForjaError
    with pytest.raises(ForjaError):
        memoria.registrar_correcao(tmp_path, **_args(a="  "))
def test_duas_ocorrencias_nao_geram_proposta(tmp_path):
    from forja import memoria
    memoria.registrar_correcao(tmp_path, **_args())
    memoria.registrar_correcao(tmp_path, **_args())
    assert not (tmp_path / "propostas").exists()
def test_terceira_ocorrencia_gera_proposta_com_evidencia_e_escopo(tmp_path):
    texto = _prop(tmp_path).read_text(encoding="utf-8")
    assert "cta-final" in texto and "COMPRE AGORA" in texto
    assert "Garanta sua vaga" in texto and "Escopo" in texto
def test_outro_padrao_nao_conta_para_o_limiar(tmp_path):
    from forja import memoria
    memoria.registrar_correcao(tmp_path, **_args(p="tom-titulo"))
    memoria.registrar_correcao(tmp_path, **_args(p="tom-titulo"))
    memoria.registrar_correcao(tmp_path, **_args(p="cta-final"))
    assert not (tmp_path / "propostas").exists()
def test_proposta_apenas_sugere_sem_tocar_no_lint(tmp_path):
    assert _prop(tmp_path).is_file()
    assert list(tmp_path.rglob("*lint*")) == []
def test_aprovar_proposta_exige_nome_do_dono(tmp_path):
    from forja import memoria
    from forja.errors import ForjaError
    _prop(tmp_path)
    with pytest.raises(ForjaError):
        memoria.decidir_proposta(tmp_path, "regra-cta-final.md", decisao="aprovar", por="  ")
def test_aprovar_proposta_registra_decisao_do_dono(tmp_path):
    from forja import memoria
    _prop(tmp_path)
    dec = memoria.decidir_proposta(tmp_path, "regra-cta-final.md", decisao="aprovar", por="Dono")
    linhas = (tmp_path / "propostas" / "decisoes.jsonl").read_text(encoding="utf-8").splitlines()
    assert dec == {"regra": "regra-cta-final.md", "decisao": "aprovar", "por": "Dono"}
    assert json.loads(linhas[-1]) == dec
def test_rejeitar_proposta_arquiva_o_arquivo(tmp_path):
    from forja import memoria
    proposta = _prop(tmp_path)
    memoria.decidir_proposta(tmp_path, "regra-cta-final.md", decisao="rejeitar", por="Dono")
    assert not proposta.exists()
    assert (tmp_path / "propostas" / "arquivadas" / "regra-cta-final.md").is_file()
def test_padrao_com_parent_dir_e_rejeitado_sem_escrever(tmp_path):
    from forja import memoria
    from forja.errors import ForjaError
    with pytest.raises(ForjaError):
        memoria.registrar_correcao(tmp_path, **_args(p="../fora"))
    assert not (tmp_path / "memoria-correcoes.jsonl").exists()
    assert list(tmp_path.rglob("*.md")) == []
def test_jsonl_truncado_falha_fechado(tmp_path):
    from forja import memoria
    from forja.errors import ForjaError
    (tmp_path / "memoria-correcoes.jsonl").write_text('{"antes": "x"}\n{truncado', encoding="utf-8")
    with pytest.raises(ForjaError):
        memoria.registrar_correcao(tmp_path, **_args())
