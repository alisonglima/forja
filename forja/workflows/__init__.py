from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points

from ..errors import ForjaError

_LOAD_ERRORS: list[dict] = []
_LOADED_GROUPS: set[str] = set()


@dataclass(frozen=True)
class Workflow:
    """Workflow registrado: resumo, fabrica de passos e arquivos do projeto."""

    name: str
    summary: str
    steps_factory: object
    files: dict


WORKFLOWS: dict[str, Workflow] = {}


def register_workflow(name, summary, steps_factory, files):
    """Registra um workflow pelo nome; nomes repetidos sao recusados."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("nome de workflow invalido: %r" % (name,))
    if not callable(steps_factory):
        raise ValueError("steps_factory de %r deve ser chamavel" % (name,))
    if name in WORKFLOWS:
        raise ValueError("workflow %r ja registrado; escolha outro nome" % (name,))
    workflow = Workflow(
        name=name,
        summary=str(summary),
        steps_factory=steps_factory,
        files=files if isinstance(files, dict) else {},
    )
    WORKFLOWS[name] = workflow
    return workflow


def get_workflow(name):
    """Devolve o workflow registrado; desconhecido vira CONFIG_INVALID."""
    workflow = WORKFLOWS.get(name)
    if workflow is not None:
        return workflow
    names = sorted(WORKFLOWS)
    listed = ", ".join(names) if names else "nenhum"
    raise ForjaError(
        "CONFIG_INVALID",
        "workflow %r desconhecido; disponiveis: %s" % (name, listed),
        hint="use um dos nomes disponiveis ou registre um workflow",
        details={"name": name, "available": names},
    )


def _discover(group):
    try:
        return entry_points(group=group)
    except TypeError:
        return entry_points().get(group, [])
    except Exception as exc:
        _LOAD_ERRORS.append(_load_error(None, group, exc))
        return []


def _selected(discovered, group):
    selector = getattr(discovered, "select", None)
    if callable(selector):
        return selector(group=group)
    getter = getattr(discovered, "get", None)
    if callable(getter):
        return getter(group, [])
    return discovered


def _load_error(entry_point, group, exc):
    name = getattr(entry_point, "name", None) or "?"
    return {
        "group": group,
        "name": name,
        "error": "falha ao carregar workflow %s: %s" % (name, exc),
    }


def reset_for_tests():
    """Limpa o estado de carregamento de plugins (usado pelas fixtures)."""
    _LOADED_GROUPS.clear()
    _LOAD_ERRORS.clear()


def load_entry_points(group="forja.workflows"):
    """Carrega plugins do grupo; falha de um plugin nao derruba os demais."""
    if group in _LOADED_GROUPS:
        return []
    _LOADED_GROUPS.add(group)
    loaded = []
    for entry_point in _selected(_discover(group), group):
        try:
            plugin = entry_point.load()
            if (
                callable(plugin)
                and not isinstance(plugin, type)
                and not getattr(plugin, "__forja_registered__", None)
            ):
                plugin()
        except Exception as exc:
            _LOAD_ERRORS.append(_load_error(entry_point, group, exc))
            continue
        loaded.append(entry_point)
    return loaded
