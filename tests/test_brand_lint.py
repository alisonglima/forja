"""Contrato `forja/brand_lint.py::lint_brand` (plano:766; regras plano:730).
`lint_brand(html,tokens,variant,fonts=None,logos=None,rules=None)->list[dict]`
com `level`/`code`/`msg` (plano:771); hex valido = paleta da variante+neutros
(`#00338D` invalido em `leo`; plano:62,1981-1983); emblema por variante
(plano:1981-1983); Roboto substituta (plano:1437); proibidos: emoji como icone,
gradiente generico, 3+ acentos, sombra/contorno; `background-image` sinaliza
revisao humana (plano:730). `variant` obrigatorio (plano:766,217)."""
import pytest
N=["#FFFFFF","#F4F4F2","#0D2240","#55565A","#B3B2B1"]
def _tokens():
    # LACUNA: formato de `tokens` nao fixado (só paleta-da-variante+neutros,
    # plano:766); fixture usa recorte minimo com hex literais plano:62,1981-83.
    return {"neutrals":list(N),"variants":{"lions":["#00338D","#EBB700","#7A2582","#407CCA","#00AB68","#FF5B35"],"leo":["#55565A","#EBB700","#407CCA","#00AB68"],"leo-lion":["#00338D","#55565A","#407CCA","#EBB700"]}}
def _exige(issues):
    assert issues!=[] and all(set(i)>={"level","code","msg"} for i in issues)
def test_peca_lions_conforme_sem_issues():
    from forja import brand_lint
    assert brand_lint.lint_brand('<p style="color: #00338D; font-family: Roboto;">Nós Servimos</p>',_tokens(),"lions")==[]
def test_peca_leo_conforme_sem_issues():
    from forja import brand_lint
    assert brand_lint.lint_brand('<p style="color: #00AB68; font-family: Roboto;">Leos get things done.</p>',_tokens(),"leo")==[]
def test_peca_leo_lion_aceita_azul_287():
    from forja import brand_lint
    assert brand_lint.lint_brand('<p style="color: #00338D; font-family: Roboto;">A new breed of Lion.</p>',_tokens(),"leo-lion")==[]
def test_azul_287_em_leo_e_erro():
    from forja import brand_lint
    _exige(brand_lint.lint_brand('<p style="color: #00338D;">Texto em azul</p>',_tokens(),"leo"))
def test_cor_fora_da_paleta_em_lions_e_erro():
    from forja import brand_lint
    _exige(brand_lint.lint_brand('<p style="color: #123456;">Texto fora da paleta</p>',_tokens(),"lions"))
def test_fonte_nao_autorizada_e_erro():
    from forja import brand_lint
    _exige(brand_lint.lint_brand('<p style="color: #0D2240; font-family: Comic Sans MS;">Texto</p>',_tokens(),"lions"))
def test_emblema_lions_proibido_em_leo():
    from forja import brand_lint
    _exige(brand_lint.lint_brand('<img src="logos/Emblemas_do_Lions/e.png" width="240" height="120">',_tokens(),"leo"))
def test_emblema_leo_permitido_em_leo():
    from forja import brand_lint
    assert brand_lint.lint_brand('<img src="logos/Emblemas_de_Leos/e.png" width="240" height="120">',_tokens(),"leo")==[]
def test_logo_1x1_abaixo_do_minimo_e_erro():
    from forja import brand_lint
    # LACUNA: plano:730 nao da o minimo em px; 1x1 esta abaixo sem fixar numero.
    _exige(brand_lint.lint_brand('<img src="logos/Emblemas_de_Leos/e.png" width="1" height="1">',_tokens(),"leo"))
def test_emoji_como_icone_e_erro():
    from forja import brand_lint
    _exige(brand_lint.lint_brand('<span class="icon" style="color: #0D2240;">\U0001F389</span>',_tokens(),"lions"))
def test_gradiente_generico_e_erro():
    from forja import brand_lint
    _exige(brand_lint.lint_brand('<div style="background: linear-gradient(#00338D, #EBB700);">T</div>',_tokens(),"lions"))
def test_quatro_acentos_distintos_e_erro():
    from forja import brand_lint
    # LACUNA: "3+ acentos" (plano:730) sem contagem; 4 hex validos cobre tudo.
    _exige(brand_lint.lint_brand('<span style="color: #00338D;">a</span><span style="color: #EBB700;">b</span><span style="color: #7A2582;">c</span><span style="color: #FF5B35;">d</span>',_tokens(),"lions"))
def test_dois_acentos_sao_permitidos():
    from forja import brand_lint
    assert brand_lint.lint_brand('<span style="color: #00338D;">a</span><span style="color: #EBB700;">b</span>',_tokens(),"lions")==[]
def test_sombra_decorativa_e_erro():
    from forja import brand_lint
    _exige(brand_lint.lint_brand('<div style="color: #00338D; box-shadow: 4px 4px 8px #0D2240;">T</div>',_tokens(),"lions"))
def test_background_image_sinaliza_revisao_humana():
    from forja import brand_lint
    # LACUNA: plano:730 nao fixa `level`/`code`; congela só sinalizacao completa.
    _exige(brand_lint.lint_brand('<div style="background-image: url(fotos/a.jpg); color: #00338D;">T</div>',_tokens(),"lions"))
def test_html_vazio_sem_violacao():
    from forja import brand_lint
    assert brand_lint.lint_brand("",_tokens(),"lions")==[]
def test_variant_ausente_nao_aprova_em_silencio():
    from forja import brand_lint
    # LACUNA: `variant` exigida (plano:766) sem codigo do lint; congela sem aprovacao.
    with pytest.raises(Exception):
        brand_lint.lint_brand("<p>Oi</p>",_tokens(),None)
def test_variant_desconhecida_nao_aprova_em_silencio():
    from forja import brand_lint
    with pytest.raises(Exception):
        brand_lint.lint_brand("<p>Oi</p>",_tokens(),"inexistente")
def test_tokens_de_tipo_errado_levanta_erro():
    from forja import brand_lint
    with pytest.raises(Exception):
        brand_lint.lint_brand("<p>Oi</p>","nao-um-dict","lions")
def test_html_nulo_levanta_erro():
    from forja import brand_lint
    with pytest.raises(Exception):
        brand_lint.lint_brand(None,_tokens(),"lions")
