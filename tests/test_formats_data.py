"""Contrato forja/data/formats.json (N-10; teste L-T-FMTD-01).
Congela plano:726 (campos), plano:39 (20 linhas §4.3.1), plano:294
(schema+exemplo), plano:334 (status/verificacao/fonte/datas),
plano:338 (rejeita sem fonte/checked_at; plano:->provisorio+[];
constantes vazia sem VERIFICADO; stale 90d e aviso); lanes
plano:802/834. Le JSON dentro do teste; relogio injetado.
"""
import json

import pytest
from datetime import date
from pathlib import Path

def _data():
    return Path(__file__).resolve().parents[1]/"forja"/"data"/"formats.json"

def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def _base(**kw):
    b={"fonte":"https://x","largura":1080,"altura":1350,"fonte_tipo":"oficial","checked_at":"2026-11-11","verificado_em":"2026-11-11","status":"provisorio","verificacao":"NAO_VERIFICADA","constantes":[]}
    b.update(kw);return b

def _erros(l):
    e=[];ft=l.get("fonte_tipo");f=str(l.get("fonte",""))
    if not l.get("fonte")or not l.get("checked_at"):e.append("rejeitada")
    if ft not in("oficial","parceiro","plano"):e.append("fonte_tipo")
    if l.get("status")not in("confirmado","provisorio"):e.append("status")
    if l.get("verificacao")not in("VERIFICADO","DIVERGENTE","NAO_VERIFICADA"):e.append("verificacao")
    if l.get("status")=="confirmado"and l.get("verificacao")!="VERIFICADO":e.append("confirmado-so-com-verificado")
    if ft=="oficial"and not f.startswith(("http://","https://")):e.append("fonte-url")
    if ft=="plano"and(not f.startswith("plano:")or l.get("status")!="provisorio"or l.get("constantes",[])!=[]):e.append("plano-provisorio")
    if l.get("verificacao")!="VERIFICADO"and l.get("constantes",[])!=[]:e.append("constantes-vazia")
    if"verificado_em"in l and l.get("checked_at")!=l.get("verificado_em"):e.append("datas-iguais")
    if not isinstance(l.get("largura"),(int,float))or not isinstance(l.get("altura"),(int,float)):e.append("dimensao")
    return e

def _stale(iso,hoje,dias=90):
    return(hoje-date.fromisoformat(iso)).days>dias

def _ok(n):
    p=Path(n);return not(p.is_absolute()or".."in p.parts)

def test_topo_tem_schema_e_20_linhas():
    d=_load(_data())
    assert d["schema_version"]==1 and d["atualizado_em"]=="2026-11-11"
    assert isinstance(d["formatos"],list)and len(d["formatos"])==20

def test_campos_obrigatorios_por_linha():
    d=_load(_data())
    req=("id","plataforma","formato","largura","altura","razao","safe_zone","max_chars","max_hashtags","alt_max","fonte","fonte_tipo","checked_at","status","notas")
    assert all(all(k in l for k in req)and _erros(l)==[]for l in d["formatos"])

def test_safe_zone_tem_margens():
    d=_load(_data())
    assert all(set(("top","bottom","left","right"))<=set(l["safe_zone"])for l in d["formatos"])

def test_checked_at_igual_verificado_em():
    d=_load(_data())
    assert all(l["checked_at"]==l["verificado_em"]for l in d["formatos"])

def test_rejeita_linha_sem_fonte_ou_checked():
    assert"rejeitada"in _erros(_base(fonte="",checked_at=""))

def test_formatos_vazio_e_fonte_oficial_sem_http(tmp_path):
    p=tmp_path/"f.json";p.write_text(json.dumps({"schema_version":1,"formatos":[]}),encoding="utf-8")
    assert _load(p)["formatos"]==[]
    assert"fonte-url"in _erros(_base(fonte="ftp://x"))

def test_plano_exige_provisorio_e_constantes_vazia():
    assert _erros(_base(fonte="plano:§4.3.1",fonte_tipo="plano"))==[]
    assert"plano-provisorio"in _erros(_base(fonte="plano:§4.3.1",fonte_tipo="plano",status="confirmado"))

def test_constantes_vazia_sem_verificado():
    assert"constantes-vazia"in _erros(_base(verificacao="DIVERGENTE",constantes=["largura"]))

def test_FORMAT_STALE_acima_de_90_dias_com_tempo_injetado():
    assert _stale("2026-06-01",date(2026,11,11))is True
    assert _stale("2026-11-11",date(2026,11,11))is False

def test_rejeita_truncado_ausente_dotdot_e_tipo_errado(tmp_path):
    p=tmp_path/"q.json";p.write_text('{"schema_version":1,"formatos":[',encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):_load(p)
    with pytest.raises(FileNotFoundError):_load(tmp_path/"ausente.json")
    assert _ok("../forja/data/formats.json")is False and _ok("formats.json")is True
    assert"dimensao"in _erros(_base(largura="1080"))
    # LACUNA: plano:334 nao rege URL de fonte_tipo parceiro.
    # LACUNA: limite_bytes/duracao_max_s/max_slides so no exemplo plano:294.
