"""Contrato de `forja describe` para o estudio (T-DESC-01).
Congela L-DESC-01: `mcp_tools` novo de `mcp.TOOLS` local (plano:559,602);
`approve` ganha `--brief/--post/--hash` (plano:532); `post` e `lote-digital`
derivam `steps{name,doc,needs}` + `files` sem lista fixa (plano:559,404);
`exit_codes` 0..5 e `error_codes` dinamicos (plano:402,465,403); envelope (plano:401).
LACUNA: texto CLI/deliver/google/slides fora desta lane; sem leitura de arquivo.
"""
import inspect


def test_top_level_ganha_mcp_tools():
    from forja import describe

    data = describe.describe({}, "1.0.0")
    assert set(data) == {"version", "exit_codes", "error_codes", "commands", "workflows", "providers", "schemas", "mcp_tools"}


def test_version_passthrough():
    from forja import describe

    assert describe.describe({}, "9.9.9")["version"] == "9.9.9"


def test_mcp_tools_espelham_tools():
    from forja import describe, mcp

    data = describe.describe({}, "1.0.0")
    assert [t["name"] for t in data["mcp_tools"]] == [t["name"] for t in mcp.TOOLS]


def test_mcp_tools_tem_nome_args_retorno():
    from forja import describe

    tools = describe.describe({}, "1.0.0")["mcp_tools"]
    assert len(tools) > 0 and all(set(t) == {"name", "args", "retorno"} for t in tools)


def test_describe_importa_tools_dentro_da_funcao():
    from forja import describe

    assert "TOOLS" in inspect.getsource(describe.describe)
    top = inspect.getsource(describe).partition("def describe(")[0]
    assert "mcp" not in top and "TOOLS" not in top


def test_approve_tem_brief_post_hash():
    from forja import describe

    cmd = next(c for c in describe.describe({}, "1.0.0")["commands"] if c["name"] == "approve")
    assert {"--script", "--voice", "--overlays", "--publish", "--by", "--brief", "--post", "--hash"} <= {a["name"] for a in cmd["args"]}


def test_commands_mantem_forma():
    from forja import describe

    cmds = describe.describe({}, "1.0.0")["commands"]
    assert cmds and all({"name", "summary", "args"} <= set(c) for c in cmds)


def test_workflows_post_e_lote_derivam_steps():
    from forja import describe

    wf = {"summary": "S", "steps": [{"name": "brief", "doc": "B", "needs": []}], "files": {"agent_writes": ["work/brief.json"]}}
    data = describe.describe({"post": wf, "lote-digital": wf}, "1.0.0")
    for key in ("post", "lote-digital"):
        assert data["workflows"][key]["steps"] == [{"name": "brief", "doc": "B", "needs": []}]
        assert data["workflows"][key]["files"] == {"agent_writes": ["work/brief.json"]}


def test_error_codes_espelham_errors():
    from forja import describe, errors

    assert set(describe.describe({}, "1.0.0")["error_codes"]) == set(errors.ERROR_CODES)


def test_exit_codes_0_a_5():
    from forja import describe

    assert set(describe.describe({}, "1.0.0")["exit_codes"]) == {0, 1, 2, 3, 4, 5}


def test_workflows_vazio_mantem_mcp_tools():
    from forja import describe, mcp

    data = describe.describe({}, "2.0.0")
    assert data["workflows"] == {} and len(data["mcp_tools"]) == len(mcp.TOOLS)


# LACUNA: describe(workflows, version) nao le arquivo/JSON; sem caso hostil de caminho/JSON truncado.
# LACUNA: `required` de --by em post e valores de `retorno` por tool nao decididos no describe estatico.
# LACUNA: literais novos de ERROR_CODES pertencem a T-ERR-01; aqui so igualdade dinamica.
