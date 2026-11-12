"""Contrato T-CAL-CADENCIA-01: cadencia semanal e grade de causas (aviso)."""
import pytest


def test_cadence_ideal_sem_issue():
    from forja import calendario
    assert calendario.check_cadence(["2027-02-01", "2027-02-02", "2027-02-08", "2027-02-09"]) == []


def test_cadence_gap_e_abaixo_do_ideal():
    from forja import calendario
    issues = calendario.check_cadence(["2027-02-01", "2027-02-15"])
    assert [(i["id"], i["level"], i["code"]) for i in issues] == [
        ("2027-W05", "info", "CADENCE_BELOW_IDEAL"),
        ("2027-W06", "warn", "CADENCE_GAP"),
        ("2027-W07", "info", "CADENCE_BELOW_IDEAL"),
    ]


def test_cadence_virada_de_ano():
    from datetime import date
    from forja import calendario
    datas = ["2026-12-28", "2027-01-05"]
    ids = [f"{date.fromisoformat(d).isocalendar()[0]}-W{date.fromisoformat(d).isocalendar()[1]:02d}" for d in datas]
    assert ids == ["2026-W53", "2027-W01"]
    issues = calendario.check_cadence(datas)
    assert [(i["id"], i["level"], i["code"]) for i in issues] == [
        ("2026-W53", "info", "CADENCE_BELOW_IDEAL"),
        ("2027-W01", "info", "CADENCE_BELOW_IDEAL"),
    ]


def test_cadence_limiares_custom():
    from forja import calendario
    datas = ["2027-02-01", "2027-02-02", "2027-02-08", "2027-02-09"]
    issues = calendario.check_cadence(datas, minimo=2, ideal=(3, 4))
    assert [(i["id"], i["level"], i["code"]) for i in issues] == [
        ("2027-W05", "info", "CADENCE_BELOW_IDEAL"),
        ("2027-W06", "info", "CADENCE_BELOW_IDEAL"),
    ]


def test_cadence_vazia_ou_none():
    from forja import calendario
    assert calendario.check_cadence([]) == []
    assert calendario.check_cadence(None) == []


def test_cadence_data_invalida():
    from forja import calendario
    from forja.errors import ForjaError
    with pytest.raises(ForjaError) as exc1:
        calendario.check_cadence(["2027-13-40"])
    assert exc1.value.code == "CONFIG_INVALID"
    with pytest.raises(ForjaError) as exc2:
        calendario.check_cadence([123])
    assert exc2.value.code == "CONFIG_INVALID"


def test_grid_quarta_e_rodizio():
    from forja import calendario
    grid = calendario.weekly_grid(["Visão", "Diabetes", "Fome"], 5, "2027-02-17")
    assert grid == [
        {"semana": "2027-W07", "segunda": "2027-02-15", "causa": "Visão"},
        {"semana": "2027-W08", "segunda": "2027-02-22", "causa": "Diabetes"},
        {"semana": "2027-W09", "segunda": "2027-03-01", "causa": "Fome"},
        {"semana": "2027-W10", "segunda": "2027-03-08", "causa": "Visão"},
        {"semana": "2027-W11", "segunda": "2027-03-15", "causa": "Diabetes"},
    ]


def test_grid_invalido():
    from forja import calendario
    from forja.errors import ForjaError
    with pytest.raises(ForjaError) as exc1:
        calendario.weekly_grid([], 3, "2027-02-17")
    assert exc1.value.code == "CONFIG_INVALID"
    with pytest.raises(ForjaError) as exc2:
        calendario.weekly_grid(["Visão"], 0, "2027-02-17")
    assert exc2.value.code == "CONFIG_INVALID"
