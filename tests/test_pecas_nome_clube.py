"""Regra do dono (13/11/2026): peças LEO levam "LEO Clube de Taquaritinga"; peças Lions levam "Lions Clube de Taquaritinga"."""
import json
import pathlib

PECAS = pathlib.Path(__file__).resolve().parents[1] / "docs/estudio/peca-real-leo/pecas.json"
NOME = {"leo": "LEO Clube de Taquaritinga", "leo-lion": "LEO Clube de Taquaritinga", "lions": "Lions Clube de Taquaritinga"}


def test_todas_as_pecas_usam_o_nome_do_clube_de_taquaritinga():
    pecas = json.loads(PECAS.read_text(encoding="utf-8"))["pecas"]
    com_clube = [p for p in pecas if "clube" in p.get("copy", {})]
    assert len(com_clube) >= 20
    for p in com_clube:
        assert p["copy"]["clube"].startswith(NOME[p["marca"]]), (p["id"], p["copy"]["clube"])
