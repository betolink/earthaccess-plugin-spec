"""Minimal entry-point discovery.

The full registry (with the ``ea.plugins`` namespace, table repr and
``list_plugins``) lives in earthaccess core. This helper is what the contract
needs to answer "which installed plugins accept these results?" without a hard
dependency on core.
"""

from __future__ import annotations

import logging
from importlib import metadata

__all__ = ["GROUP", "installed_plugins"]

GROUP = "earthaccess.plugins"
_RESERVED = {"get", "available"}

_LOGGER = logging.getLogger("earthaccess.plugins")


def installed_plugins(group: str = GROUP) -> dict[str, type]:
    """Return ``{name: plugin_class}`` for installed entry points.

    A plugin that fails to import is skipped with a warning; discovery never
    imports a backend (plugin modules import their backend lazily).
    """

    found: dict[str, type] = {}
    try:
        entry_points = metadata.entry_points(group=group)
    except Exception as exc:  # noqa: BLE001 - discovery must never raise
        _LOGGER.warning("could not read entry points: %s", exc)
        return found
    for ep in sorted(entry_points, key=lambda e: e.name):
        if ep.name in _RESERVED or ep.name in found:
            continue
        try:
            found[ep.name] = ep.load()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("failed to load plugin %r: %s", ep.name, exc)
    return found
