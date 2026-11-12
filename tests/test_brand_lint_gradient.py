"""Contrato do degrade de marca autorizado (`allow_brand_gradient`)."""
N=["#FFFFFF","#F4F4F2","#0D2240","#55565A","#B3B2B1"]
def _tokens():
    return {"neutrals":list(N),"variants":{"lions":["#00338D","#EBB700","#7A2582","#407CCA","#00AB68","#FF5B35"],"leo":["#55565A","#EBB700","#407CCA","#00AB68"],"leo-lion":["#00338D","#55565A","#407CCA","#EBB700"]}}
def _grad(issues):
    return [i for i in issues if i["code"]=="BRAND_GENERIC_GRADIENT"]
def test_sem_flag_paleta_ainda_e_generico():
    from forja import brand_lint
    issues=brand_lint.lint_brand('<div style="background: linear-gradient(#00338D, #7A2582)">T</div>',_tokens(),"lions")
    grad=_grad(issues)
    assert len(grad)==1 and grad[0]["level"]=="error"
def test_com_flag_paleta_hex_autorizado():
    from forja import brand_lint
    issues=brand_lint.lint_brand('<div style="background: linear-gradient(#00338D, #7A2582)">T</div>',_tokens(),"lions",rules={"allow_brand_gradient":True})
    assert _grad(issues)==[]
def test_com_flag_var_declarado_no_root_autorizado():
    from forja import brand_lint
    html='<style>:root{--a:#00338D;--b:#7A2582}</style><div style="background:linear-gradient(45deg, var(--a) 0%, var(--b) 100%)">T</div>'
    issues=brand_lint.lint_brand(html,_tokens(),"lions",rules={"allow_brand_gradient":True})
    assert _grad(issues)==[]
def test_com_flag_hex_fora_da_paleta_e_erro_e_cor():
    from forja import brand_lint
    issues=brand_lint.lint_brand('<div style="background: linear-gradient(#00338D, #FF00FF)">T</div>',_tokens(),"lions",rules={"allow_brand_gradient":True})
    grad=_grad(issues)
    assert len(grad)==1 and grad[0]["level"]=="error"
    assert "BRAND_COLOR_INVALID" in [i["code"] for i in issues]
def test_com_flag_rgba_e_erro():
    from forja import brand_lint
    issues=brand_lint.lint_brand('<div style="background: linear-gradient(rgba(0,0,0,.5), #00338D)">T</div>',_tokens(),"lions",rules={"allow_brand_gradient":True})
    grad=_grad(issues)
    assert len(grad)==1 and grad[0]["level"]=="error"
def test_com_flag_cor_nomeada_red_e_erro():
    from forja import brand_lint
    issues=brand_lint.lint_brand('<div style="background: linear-gradient(red, #00338D)">T</div>',_tokens(),"lions",rules={"allow_brand_gradient":True})
    grad=_grad(issues)
    assert len(grad)==1 and grad[0]["level"]=="error"
def test_com_flag_transparent_e_erro():
    from forja import brand_lint
    issues=brand_lint.lint_brand('<div style="background: linear-gradient(transparent, #00338D)">T</div>',_tokens(),"lions",rules={"allow_brand_gradient":True})
    grad=_grad(issues)
    assert len(grad)==1 and grad[0]["level"]=="error"
def test_com_flag_var_sem_declaracao_e_erro():
    from forja import brand_lint
    issues=brand_lint.lint_brand('<div style="background: linear-gradient(var(--x), #00338D)">T</div>',_tokens(),"lions",rules={"allow_brand_gradient":True})
    grad=_grad(issues)
    assert len(grad)==1 and grad[0]["level"]=="error"
def test_leo_com_flag_azul_287_e_erro():
    from forja import brand_lint
    issues=brand_lint.lint_brand('<div style="background: linear-gradient(#00338D, #EBB700)">T</div>',_tokens(),"leo",rules={"allow_brand_gradient":True})
    grad=_grad(issues)
    assert len(grad)==1 and grad[0]["level"]=="error"
def test_dois_gradientes_um_autorizado_um_nao_da_um_erro():
    from forja import brand_lint
    html='<div style="background: linear-gradient(#00338D, #7A2582)">A</div><div style="background: linear-gradient(#00338D, #FF00FF)">B</div>'
    issues=brand_lint.lint_brand(html,_tokens(),"lions",rules={"allow_brand_gradient":True})
    grad=_grad(issues)
    assert len(grad)==1 and grad[0]["level"]=="error"
def test_flag_yes_nao_autoriza():
    from forja import brand_lint
    issues=brand_lint.lint_brand('<div style="background: linear-gradient(#00338D, #7A2582)">T</div>',_tokens(),"lions",rules={"allow_brand_gradient":"yes"})
    grad=_grad(issues)
    assert len(grad)==1 and grad[0]["level"]=="error"
def test_flag_1_nao_autoriza():
    from forja import brand_lint
    issues=brand_lint.lint_brand('<div style="background: linear-gradient(#00338D, #7A2582)">T</div>',_tokens(),"lions",rules={"allow_brand_gradient":1})
    grad=_grad(issues)
    assert len(grad)==1 and grad[0]["level"]=="error"
def test_rules_none_nao_autoriza():
    from forja import brand_lint
    issues=brand_lint.lint_brand('<div style="background: linear-gradient(#00338D, #7A2582)">T</div>',_tokens(),"lions",rules=None)
    grad=_grad(issues)
    assert len(grad)==1 and grad[0]["level"]=="error"
def test_rules_vazio_nao_autoriza():
    from forja import brand_lint
    issues=brand_lint.lint_brand('<div style="background: linear-gradient(#00338D, #7A2582)">T</div>',_tokens(),"lions",rules={})
    grad=_grad(issues)
    assert len(grad)==1 and grad[0]["level"]=="error"
