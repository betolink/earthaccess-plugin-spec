"""The results a plugin consumes: a small protocol plus an adapter.

``search_data()`` already returns full UMM, so nothing has to be hydrated here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

__all__ = ["GranuleResultSet", "ResultSet", "as_result_set"]


@runtime_checkable
class ResultSet(Protocol):
    """The minimal shape a plugin needs from search results."""

    collection_id: str
    """Concept id of the single collection the granules belong to."""

    ids: Sequence[str]
    """Granule concept ids (``meta.concept-id``)."""

    native_ids: Sequence[str]
    """Granule URs / names (``umm.GranuleUR``)."""

    def umm(self) -> Sequence[Mapping[str, Any]]:
        """Return the raw UMM-G records."""
        ...


class GranuleResultSet:
    """Adapter over the plain ``list[dict]`` returned by ``search_data()``."""

    def __init__(self, granules: Sequence[Mapping[str, Any]]) -> None:
        self._granules = list(granules)
        collections = {g["meta"]["collection-concept-id"] for g in self._granules}
        if len(collections) > 1:
            raise ValueError("a ResultSet holds granules from one collection")
        self.collection_id = next(iter(collections), "")
        self.ids = [g["meta"]["concept-id"] for g in self._granules]
        self.native_ids = [g["umm"]["GranuleUR"] for g in self._granules]

    def umm(self) -> list[Mapping[str, Any]]:
        return [g["umm"] for g in self._granules]


def as_result_set(results: Any) -> Any:
    """Wrap a plain list of granules, pass through a ResultSet or ``None``."""

    if results is None or hasattr(results, "collection_id"):
        return results
    return GranuleResultSet(results)
