"""The results a plugin consumes: a protocol, an adapter and support listing.

`search_data()` already returns full UMM, so nothing has to be hydrated here.
`GranuleResultSet` is a ``list`` subclass so existing list-based code keeps
working, while slicing preserves the type (and therefore the extra methods).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from .support import ServiceRow, ServiceTable
from .version import CONTRACT_VERSION

if TYPE_CHECKING:
    from .context import PluginContext

__all__ = ["GranuleResultSet", "ResultSet", "as_result_set"]


@runtime_checkable
class ResultSet(Protocol):
    """The minimal shape a plugin needs from search results."""

    collection_id: str
    """Concept id of the single collection the granules belong to."""

    short_name: str
    """Collection short name (from the granule's UMM CollectionReference)."""

    version: str
    """Collection version (from the granule's UMM CollectionReference)."""

    ids: Sequence[str]
    """Granule concept ids (``meta.concept-id``)."""

    native_ids: Sequence[str]
    """Granule URs / names (``umm.GranuleUR``)."""

    def umm(self) -> Sequence[Mapping[str, Any]]:
        """Return the raw UMM-G records."""
        ...

    def services(self) -> Sequence[Mapping[str, Any]]:
        """Return the UMM-S records associated with the collection (may be empty)."""
        ...

    def list_services(self, context: PluginContext | None = None) -> ServiceTable:
        """Return which installed plugins accept these results."""
        ...


def _collection_reference(granule: Mapping[str, Any]) -> Mapping[str, Any]:
    return granule.get("umm", {}).get("CollectionReference", {}) or {}


class GranuleResultSet(list):
    """Adapter over the plain ``list[dict]`` returned by ``search_data()``."""

    def __init__(
        self,
        granules: Sequence[Mapping[str, Any]],
        *,
        services: Sequence[Mapping[str, Any]] | None = None,
    ) -> None:
        super().__init__(granules)
        collections = {g["meta"]["collection-concept-id"] for g in self}
        if len(collections) > 1:
            raise ValueError("a ResultSet holds granules from one collection")
        self.collection_id = next(iter(collections), "")
        self.ids = [g["meta"]["concept-id"] for g in self]
        self.native_ids = [g["umm"]["GranuleUR"] for g in self]
        reference = _collection_reference(self[0]) if self else {}
        self.short_name = reference.get("ShortName", "")
        self.version = reference.get("Version", "")
        self._services = list(services) if services else []

    def __getitem__(self, key: Any) -> Any:
        result = super().__getitem__(key)
        if isinstance(key, slice):
            # Slicing must preserve the type, or the extra methods are lost.
            return GranuleResultSet(result, services=self._services)
        return result

    def umm(self) -> list[Mapping[str, Any]]:
        return [g["umm"] for g in self]

    def services(self) -> list[Mapping[str, Any]]:
        return list(self._services)

    def list_services(self, context: PluginContext | None = None) -> ServiceTable:
        return list_services(self, context)


def as_result_set(results: Any) -> Any:
    """Wrap a plain list of granules, pass through a ResultSet or ``None``."""

    if results is None or hasattr(results, "collection_id"):
        return results
    return GranuleResultSet(results)


def list_services(results: Any, context: PluginContext | None = None) -> ServiceTable:
    """Query every installed plugin for support of ``results``.

    Plugins that are not installed cannot be checked and are not listed, and a
    plugin whose check errors is shown as ``?`` rather than failing the table.
    """

    from .context import default_context
    from .discovery import installed_plugins

    if context is None:
        context = default_context()
    rows: list[ServiceRow] = []
    for name, plugin_cls in installed_plugins().items():
        if getattr(plugin_cls, "contract_version", None) != CONTRACT_VERSION:
            continue
        try:
            support = plugin_cls(context).supports(results)
        except Exception as exc:  # noqa: BLE001 - a broken plugin must not break the table
            rows.append(ServiceRow(name, None, f"error: {exc!r}"))
            continue
        rows.append(ServiceRow(name, support.ok, support.reason))
    return ServiceTable(rows)
