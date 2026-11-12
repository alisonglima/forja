"""Contrato de dados de `forja/data/rubrica.json` (T-JURY-DATA, N-24).

plano:750: 5 critérios, pesos 20/25/20/20/15, limiar 85/100, nenhum <3,
máximo 2 rodadas (70–84,9 corrige; abaixo de 70 bloqueia) e cada critério com
parte `measured` e `editorial`, nunca convertidas uma na outra (plano:616: nota 1–5).
LACUNA: o plano não fixa nomes de chaves nem grafia dos checks; este contrato
fixa `criteria[].{name,weight,measured,editorial}`, `scale`, `threshold`,
`min_criterion`, `max_rounds` e `correction_band`, sem caixa/acento.
LACUNA: "corrige uma vez" (plano:750) conflita com "até duas rodadas"
(plano:624/2450); vale `max_rounds` = 2.
"""
import json
import unicodedata
from pathlib import Path

RUBRICA = Path(__file__).resolve().parents[1] / "forja" / "data" / "rubrica.json"

CRITERIOS = [
    ("verdade e fonte", 20),
    ("hierarquia e legibilidade", 25),
    ("marca e identidade", 20),
    ("formato e plataforma", 20),
    ("prontidão e entrega", 15),
]
CHECKS = {"dimensao", "overflow", "contraste", "fontes", "hash", "aprovacoes", "dedup"}
EDITORIAL = {"verdade", "hierarquia", "tom"}


def _norm(text):
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in text if not unicodedata.combining(char))


def _data():
    return json.loads(RUBRICA.read_text(encoding="utf-8"))


def test_rubrica_is_a_json_object():
    assert RUBRICA.is_file()
    assert isinstance(_data(), dict)


def test_criteria_are_the_five_contract_ones_in_order():
    criteria = _data()["criteria"]
    assert [(item["name"].casefold(), item["weight"]) for item in criteria] == CRITERIOS
    assert sum(item["weight"] for item in criteria) == 100


def test_scale_threshold_and_minimum_criterion_are_exact():
    data = _data()
    assert data["scale"] == [1, 5]
    assert data["threshold"] == 85
    assert data["min_criterion"] == 3


def test_at_most_two_rounds_with_70_to_84_9_correction_band():
    data = _data()
    assert data["max_rounds"] == 2
    assert data["correction_band"] == [70, 84.9]


def test_each_criterion_has_measured_and_editorial_parts():
    for item in _data()["criteria"]:
        assert isinstance(item["measured"], list) and item["measured"]
        assert isinstance(item["editorial"], list) and item["editorial"]
        assert all(isinstance(check, str) and check for check in item["measured"])
        assert all(isinstance(role, str) and role for role in item["editorial"])
        assert set(item["measured"]).isdisjoint(item["editorial"])


def test_measured_checks_and_editorial_roles_are_the_contract_ones():
    criteria = _data()["criteria"]
    measured = {_norm(check) for item in criteria for check in item["measured"]}
    editorial = {_norm(role) for item in criteria for role in item["editorial"]}
    assert measured == CHECKS
    assert editorial == EDITORIAL
