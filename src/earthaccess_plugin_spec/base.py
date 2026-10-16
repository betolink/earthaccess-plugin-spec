"""``PluginBase``: the class every earthaccess plugin subclasses."""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar, Literal

from .context import PluginContext
from .errors import MissingResultsError, NotSupportedError
from .job import Job
from .results import as_result_set

__all__ = ["PluginBase", "validate_inputs"]

_NEEDS = {"concept_id": "ids", "native_id": "native_ids", "umm": "umm"}


def validate_inputs(plugin: PluginBase, results: Any) -> None:
    """Check the plugin's ``requires_results`` and ``needs`` against ``results``.

    ``needs`` is checked, not fetched: ``search_data()`` already returns full UMM.
    """

    if results is None:
        if plugin.requires_results:
            raise MissingResultsError(f"{plugin.name} needs search results")
        return
    for need in plugin.needs:
        value = getattr(results, _NEEDS[need], None)
        if callable(value):
            value = value()
        if not value:
            raise MissingResultsError(
                f"{plugin.name} needs {need!r}; these results do not provide it"
            )


class PluginBase:
    """Subclass this. Implement ``Options`` and ``_request``."""

    name: ClassVar[str]
    contract_version: ClassVar[int] = 1
    needs: ClassVar[frozenset[str]] = frozenset()
    requires_results: ClassVar[bool] = True
    auth: ClassVar[Literal["edl", "own", "none"]]
    output: ClassVar[str]  # 'assets' | 'xarray' | 'dataframe'
    Options: ClassVar[type]

    def __init__(self, ctx: PluginContext) -> None:
        self._ctx = ctx

    # --- implemented by the plugin ---
    def _request(self, results: Any, options: Any) -> Job:
        raise NotImplementedError

    # --- provided by the contract ---
    def job(self, fn: Any) -> Job:
        """Run ``fn`` in the shared background pool and return a local :class:`Job`."""

        return Job(fn, plugin=self.name, output=self.output)

    def request(self, results: Any = None, **options: Any) -> Job:
        """Validate inputs and return a :class:`Job` immediately."""

        # a plain list from search_data() becomes a GranuleResultSet
        results = as_result_set(results)
        validate_inputs(self, results)
        # unknown kwargs raise TypeError here
        return self._request(results, self.Options(**options))

    def run(self, results: Any = None, **options: Any) -> Any:
        """``request().results()``: block until the job settles and return its output."""

        return self.request(results, **options).results()

    def get_job(self, job_id: str) -> Job:
        """Rebuild a resumable remote job from its id. Overridden by remote plugins."""

        raise NotSupportedError(f"{self.name} jobs cannot be resumed")

    async def arequest(self, results: Any = None, **options: Any) -> Job:
        return await asyncio.to_thread(self.request, results, **options)

    async def arun(self, results: Any = None, **options: Any) -> Any:
        return await asyncio.to_thread(self.run, results, **options)
