"""Calculo deterministico do juri de revisao (rubrica de 5 criterios).

`score` combina a parte medida e a parte editorial sem converte-las uma na
outra: cada lado e pontuado de forma independente e o total e a media dos
dois. Abaixo de 70, ou com qualquer criterio abaixo do minimo, o veredito e
`bloqueado`; a faixa de correcao so pode ser usada nas duas primeiras
passadas (plano:750; DESIGN.md, secao de revisao).
"""
from __future__ import annotations

_BLOCK_BELOW = 70.0
_MAX_PASSES = 3
_APPROVED = "aprovado"
_CORRECTION = "corrige"
_BLOCKED = "bloqueado"


def _number(value, default):
    """Converte um numero da rubrica, caindo no padrao quando invalido."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


def _criteria(rubric) -> list:
    """Pares (id, peso) na ordem da rubrica; ignora itens malformados."""
    items = rubric.get("criterios") if isinstance(rubric, dict) else None
    if not isinstance(items, list):
        return []
    criteria = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        cid = item.get("id") or item.get("name") or index
        criteria.append((str(cid), _number(item.get("peso"), 0.0)))
    return criteria


def _notes(value, criteria) -> dict:
    """Notas por criterio; um escalar vale para todos os criterios."""
    if isinstance(value, dict):
        return {cid: value.get(cid) for cid, _ in criteria}
    return {cid: value for cid, _ in criteria}


def _note(value):
    """Nota numerica ou None quando ausente/invalida."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _weighted(criteria, notes) -> float:
    """Nota 0-100: soma(peso x nota) / 5; criterio sem nota vale zero."""
    total = 0.0
    for cid, weight in criteria:
        note = _note(notes.get(cid))
        total += weight * (note if note is not None else 0.0)
    return total / 5.0


def _passes(value) -> int:
    """Numero da passada atual (default 1)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 1


def score(piece, rubric, measured, editorial, *, passes=1) -> dict:
    """Calcula `medido`, `editorial`, `total`, `bloqueios` e `veredito`.

    `piece` identifica a peca revisada; a rubrica traz os criterios/pesos, o
    limiar e o minimo por criterio. `passes` conta a avaliacao atual: a faixa
    de correcao (70 a limiar-1) vale nas duas primeiras passadas.
    """
    criteria = _criteria(rubric)
    limiar = _number(rubric.get("limiar") if isinstance(rubric, dict) else None, 85.0)
    minimo = _number(rubric.get("minimo") if isinstance(rubric, dict) else None, 3.0)
    measured_notes = _notes(measured, criteria)
    editorial_notes = _notes(editorial, criteria)
    medido = _weighted(criteria, measured_notes)
    editorial_score = _weighted(criteria, editorial_notes)
    total = (medido + editorial_score) / 2.0

    bloqueios = []
    if not criteria:
        bloqueios.append("rubrica sem criterios")
    for cid, _weight in criteria:
        for lado, notes in (("medido", measured_notes),
                            ("editorial", editorial_notes)):
            note = _note(notes.get(cid))
            if note is None:
                bloqueios.append("%s: criterio %s sem nota" % (lado, cid))
            elif note < minimo:
                bloqueios.append(
                    "%s: criterio %s nota %g abaixo do minimo %g"
                    % (lado, cid, note, minimo)
                )
    if total < _BLOCK_BELOW:
        bloqueios.append("total %g abaixo de %g" % (total, _BLOCK_BELOW))

    if bloqueios:
        veredito = _BLOCKED
    elif total >= limiar:
        veredito = _APPROVED
    elif _passes(passes) >= _MAX_PASSES:
        veredito = _BLOCKED
        bloqueios.append(
            "total %g na faixa de correcao sem rodada disponivel" % total
        )
    else:
        veredito = _CORRECTION

    return {
        "medido": medido,
        "editorial": editorial_score,
        "total": total,
        "bloqueios": bloqueios,
        "veredito": veredito,
    }
