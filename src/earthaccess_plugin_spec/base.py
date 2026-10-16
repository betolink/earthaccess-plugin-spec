"""``PluginBase``: the class every earthaccess plugin subclasses."""

from __future__ import annotations

import asyncio
import warnings
from dataclasses import replace
from typing import Any, ClassVar, Literal

from .context import PluginContext
from .errors import (
    MissingResultsError,
    NotSupportedError,
    UnsupportedCollectionError,
)
from .job import Job
from .results import as_result_set
from .support import Capabilities
from .version import CONTRACT_VERSION

__all__ = ["PluginBase", "accepting_plugins", "validate_inputs", "as_target"]

_NEEDS = {"concept_id": "ids", "native_id": "native_ids", "umm": "umm"}
_RESERVED_OPTIONS = frozenset({"check"})
_warned_unknown_support: set[tuple[str, str]] = set()


class _ShortNameTarget:
    """A results-like target for ``capabilities("ATL06")`` calls."""

    def __init__(self, short_name: str) -> None:
        self.short_name = short_name
        self.version = ""
        self.collection_id = ""
        self.ids: list[str] = []
        self.native_ids: list[str] = []

    def umm(self) -> list[dict[str, Any]]:
        return []

    def services(self) -> list[dict[str, Any]]:
        return []


def as_target(target: Any) -> Any:
    """Normalise a capability-check target: a short name, results, or ``None``."""

    if target is None:
        return None
    if isinstance(target, str):
        return _ShortNameTarget(target)
    return as_result_set(target)


def _collection_label(results: Any) -> str:
    return (
        getattr(results, "short_name", "")
        or getattr(results, "collection_id", "")
        or ""
    )


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


def accepting_plugins(results: Any, exclude: Any = ()) -> list[str]:
    """Names of installed plugins whose capabilities are definitely supported."""

    from .context import default_context
    from .discovery import installed_plugins

    excluded = {exclude} if isinstance(exclude, str) else set(exclude)
    context = default_context()
    names: list[str] = []
    for name, plugin_cls in installed_plugins().items():
        if (
            name in excluded
            or getattr(plugin_cls, "contract_version", None) != CONTRACT_VERSION
        ):
            continue
        try:
            caps = plugin_cls(context).capabilities(results)
        except Exception:  # noqa: BLE001, S112 - a broken plugin must not mask the real error
            continue
        if caps.ok is True:
            names.append(name)
    return sorted(names)


def warn_once(plugin: str, collection_id: str, reason: str) -> None:
    """Warn a single time per (plugin, collection) that support is unknown."""

    key = (plugin, collection_id or "")
    if key in _warned_unknown_support:
        return
    _warned_unknown_support.add(key)
    warnings.warn(
        f"{plugin}: could not confirm support for {collection_id or 'these results'}: "
        f"{reason}",
        stacklevel=3,
    )


class PluginBase:
    """Subclass this. Implement ``Options`` and ``_request``.

    Optionally override ``_supports`` to report the collection's capabilities.
    """

    name: ClassVar[str]
    contract_version: ClassVar[int] = CONTRACT_VERSION
    needs: ClassVar[frozenset[str]] = frozenset()
    requires_results: ClassVar[bool] = True
    auth: ClassVar[Literal["edl", "own", "none"]]
    output: ClassVar[str]  # 'assets' | 'xarray' | 'dataframe'
    Options: ClassVar[type]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        fields = getattr(getattr(cls, "Options", None), "__dataclass_fields__", {})
        clash = _RESERVED_OPTIONS & set(fields)
        if clash:
            raise TypeError(
                f"{cls.__name__}.Options defines reserved option name(s): "
                f"{sorted(clash)}; 'check' is reserved by request()"
            )

    def __init__(self, ctx: PluginContext) -> None:
        self._ctx = ctx
        self._capabilities_cache: dict[str, Capabilities] = {}

    # --- implemented by the plugin ---
    def _request(self, results: Any, options: Any) -> Job:
        raise NotImplementedError

    def _supports(self, results: Any) -> Capabilities:
        """Cheap, collection-level capability check.

        Default: the plugin handles everything, with no extra detail.
        """

        return Capabilities(True)

    # --- provided by the contract ---
    def capabilities(self, target: Any = None, *, check: bool = True) -> Capabilities:
        """Return the collection's capabilities.

        ``target`` is search results or a collection short name. This is the
        primary entry point; :meth:`supports` is an alias.
        """

        results = as_target(target)
        if results is None:
            return Capabilities(True, plugin=self.name)
        key = getattr(results, "collection_id", "") or _collection_label(results)
        if key and key in self._capabilities_cache:
            return self._capabilities_cache[key]
        try:
            caps = self._supports(results)
        except Exception as exc:  # noqa: BLE001 - never let a check crash a request
            caps = Capabilities(None, reason=f"capability check failed: {exc!r}")
        if not isinstance(caps, Capabilities):
            caps = Capabilities(
                None, reason=f"_supports returned {type(caps).__name__}"
            )
        caps = replace(
            caps,
            plugin=caps.plugin or self.name,
            collection=caps.collection or _collection_label(results),
        )
        if key:
            self._capabilities_cache[key] = caps
        return caps

    def supports(self, target: Any = None, *, check: bool = True) -> Capabilities:
        """Alias of :meth:`capabilities`."""

        return self.capabilities(target, check=check)

    def job(self, fn: Any) -> Job:
        """Run ``fn`` in the shared background pool and return a local :class:`Job`."""

        return Job(fn, plugin=self.name, output=self.output)

    def request(
        self, results: Any = None, *, check: bool = True, **options: Any
    ) -> Job:
        """Validate inputs, check support, and return a :class:`Job` immediately."""

        # a plain list from search_data() becomes a GranuleResultSet
        results = as_result_set(results)
        validate_inputs(self, results)
        if check and results is not None:
            caps = self.capabilities(results)
            if caps.ok is False:
                raise UnsupportedCollectionError(
                    self.name,
                    results.collection_id,
                    short_name=getattr(results, "short_name", ""),
                    reason=caps.reason,
                    accepting=accepting_plugins(results, exclude=self.name),
                )
            if caps.ok is None:
                warn_once(self.name, results.collection_id, caps.reason)
        # unknown kwargs raise TypeError here
        return self._request(results, self.Options(**options))

    def run(self, results: Any = None, *, check: bool = True, **options: Any) -> Any:
        """``request().results()``: block until the job settles and return its output."""

        return self.request(results, check=check, **options).results()

    def get_job(self, job_id: str) -> Job:
        """Rebuild a resumable remote job from its id. Overridden by remote plugins."""

        raise NotSupportedError(f"{self.name} jobs cannot be resumed")

    async def arequest(
        self, results: Any = None, *, check: bool = True, **options: Any
    ) -> Job:
        return await asyncio.to_thread(self.request, results, check=check, **options)

    async def arun(
        self, results: Any = None, *, check: bool = True, **options: Any
    ) -> Any:
        return await asyncio.to_thread(self.run, results, check=check, **options)
