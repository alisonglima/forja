from __future__ import annotations

import importlib.metadata
import os

from .errors import ForjaError

KINDS = ("tts", "stt", "render", "clip", "image", "music")

_FACTORIES: dict[str, dict[str, object]] = {}
_META: dict[tuple[str, str], dict] = {}
_LOAD_ERRORS: list[dict] = []
_LOADED_GROUPS: set[str] = set()


def _reset_state():
    _FACTORIES.clear()
    _META.clear()
    _LOAD_ERRORS.clear()
    _LOADED_GROUPS.clear()


_reset_state()


def _kind_error(kind) -> ValueError:
    return ValueError(
        "kind de provedor invalido: %r (use um de: %s)" % (kind, ", ".join(KINDS))
    )


def _is_set(env, var) -> bool:
    value = env.get(var) if env is not None else None
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def register(kind, name, *, requires_env=(), network=False, note=""):
    """Decorador que registra uma fabrica de provedor em `kind`."""
    if kind not in KINDS:
        raise _kind_error(kind)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("nome de provedor invalido: %r" % (name,))

    def decorator(factory):
        if name in _FACTORIES.get(kind, {}):
            raise ValueError(
                "provedor %r ja registrado em %r; escolha outro nome" % (name, kind)
            )
        _FACTORIES.setdefault(kind, {})[name] = factory
        _META[(kind, name)] = {
            "requires_env": tuple(requires_env),
            "network": bool(network),
            "note": str(note),
        }
        try:
            factory.__forja_registered__ = (kind, name)
        except (AttributeError, TypeError):
            pass
        return factory

    return decorator


def get(kind, name):
    """Devolve a fabrica registrada; desconhecida vira CONFIG_INVALID."""
    factory = _FACTORIES.get(kind, {}).get(name)
    if factory is not None:
        return factory
    names = sorted(_FACTORIES.get(kind, {}))
    listed = ", ".join(names) if names else "nenhum"
    raise ForjaError(
        "CONFIG_INVALID",
        "provedor %r desconhecido para %r; disponiveis: %s" % (name, kind, listed),
        hint="use um dos nomes disponiveis ou registre um provedor com @register",
        details={"kind": kind, "name": name, "available": names},
    )


def _entry(kind, name, env) -> dict:
    meta = _META.get((kind, name), {})
    requires = tuple(meta.get("requires_env", ()))
    return {
        "kind": kind,
        "name": name,
        "requires_env": requires,
        "env_ok": all(_is_set(env, var) for var in requires),
        "network": bool(meta.get("network", False)),
        "note": meta.get("note", ""),
    }


def available(kind=None, env=None) -> list[dict]:
    """Lista provedores e se o ambiente deles esta pronto (nunca os valores)."""
    if env is None:
        env = os.environ
    if kind is not None and kind not in KINDS:
        raise _kind_error(kind)
    kinds = (kind,) if kind is not None else KINDS
    entries = []
    for current in kinds:
        for name in sorted(_FACTORIES.get(current, {})):
            entries.append(_entry(current, name, env))
    if kind is None:
        entries.extend(dict(item) for item in _LOAD_ERRORS)
    return entries


def load_entry_points(group="forja.providers"):
    """Carrega plugins do grupo; falha de um plugin vira aviso, nao excecao."""
    if group in _LOADED_GROUPS:
        return []
    _LOADED_GROUPS.add(group)
    try:
        discovered = importlib.metadata.entry_points(group=group)
    except TypeError:
        discovered = importlib.metadata.entry_points().get(group, [])
    except Exception as exc:
        _LOAD_ERRORS.append(_load_error(None, group, exc))
        return []
    try:
        selected = discovered.select(group=group)
    except AttributeError:
        selected = discovered
    loaded = []
    for entry_point in selected:
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


def _load_error(entry_point, group, exc) -> dict:
    name = getattr(entry_point, "name", None) or "?"
    value = getattr(entry_point, "value", None) or name
    return {
        "kind": None,
        "name": name,
        "requires_env": (),
        "env_ok": False,
        "network": False,
        "note": "",
        "error": "falha ao carregar plugin %s (%s): %s" % (name, value, exc),
    }


def reset_for_tests():
    """Limpa registros e avisos (usado pelas fixtures de teste)."""
    _reset_state()
