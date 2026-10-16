"""The conformance suite every plugin runs in CI.

```python
from earthaccess_plugin_spec.testing import run_conformance

def test_conformance():
    run_conformance(MyPlugin, fixtures=MyFixtures())
```
"""

from __future__ import annotations

import contextlib
from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import Any

from .base import PluginBase
from .context import PluginContext
from .job import Job, JobStatus
from .results import ResultSet

__all__ = ["FakeAuth", "Fixtures", "fake_context", "run_conformance", "sample_result_set"]

_OUTPUTS = {"assets", "xarray", "dataframe"}
_AUTHS = {"edl", "own", "none"}
_SETTLED = {
    JobStatus.PAUSED,
    JobStatus.SUCCEEDED,
    JobStatus.PARTIAL,
    JobStatus.FAILED,
    JobStatus.CANCELED,
}


class FakeAuth:
    """An :class:`AuthHandle` that never touches the network."""

    def __init__(self) -> None:
        self.session_calls = 0
        self.token_calls = 0

    def session(self) -> Any:
        self.session_calls += 1
        return object()

    def token(self) -> str:
        self.token_calls += 1
        return "conformance-token"


def fake_context(label: str = "earthaccess-conformance") -> PluginContext:
    return PluginContext(auth=FakeAuth(), label=label)


class _StubResultSet:
    """A ResultSet whose fields can be emptied one at a time."""

    def __init__(
        self,
        *,
        collection_id: str = "C1234-EXAMPLE",
        ids: Sequence[str] = ("G1234-EXAMPLE",),
        native_ids: Sequence[str] = ("G1234.EXAMPLE",),
        umms: Sequence[dict] | None = None,
    ) -> None:
        self.collection_id = collection_id
        self.ids = list(ids)
        self.native_ids = list(native_ids)
        self._umms = list(umms) if umms is not None else [{"GranuleUR": "G1234.EXAMPLE"}]

    def umm(self) -> Sequence[dict]:
        return self._umms


def sample_result_set(**kwargs: Any) -> ResultSet:
    """Build a one-granule ResultSet that satisfies every ``needs`` value."""

    return _StubResultSet(**kwargs)  # type: ignore[return-value]


@dataclass
class Fixtures:
    """Backend-specific data a plugin author supplies to the conformance suite."""

    result_set: ResultSet | None = field(default_factory=lambda: sample_result_set())
    options: dict[str, Any] = field(default_factory=dict)
    failing_options: dict[str, Any] | None = None

    def context(self) -> PluginContext:
        return fake_context()

    def backend(self) -> AbstractContextManager[Any]:
        """Patch the backend for the duration of a request (fake client, etc.)."""

        return contextlib.nullcontext()


def _missing_needs(plugin: type) -> set[str]:
    needs = set(getattr(plugin, "needs", frozenset()))
    return needs - {"concept_id", "native_id", "umm"}


def run_conformance(plugin_cls: type[PluginBase], fixtures: Fixtures | None = None) -> None:
    """Run the contract checks. Raises ``AssertionError`` listing every failure."""

    fixtures = fixtures or Fixtures()
    failures: list[str] = []

    def check(name: str, fn: Any) -> None:
        try:
            fn()
        except AssertionError as exc:
            failures.append(f"{name}: {exc}")
        except Exception as exc:  # noqa: BLE001 - report, do not mask the check
            failures.append(f"{name}: raised {type(exc).__name__}: {exc}")

    # 1. Metadata sanity -------------------------------------------------------
    def metadata() -> None:
        assert getattr(plugin_cls, "name", None), "name is required"
        assert isinstance(getattr(plugin_cls, "contract_version", None), int), (
            "contract_version must be an int"
        )
        assert plugin_cls.output in _OUTPUTS, f"output must be one of {_OUTPUTS}"
        assert plugin_cls.auth in _AUTHS, f"auth must be one of {_AUTHS}"
        assert isinstance(getattr(plugin_cls, "Options", None), type), "Options is required"
        unknown = _missing_needs(plugin_cls)
        assert not unknown, f"unknown needs: {unknown}"

    check("metadata", metadata)

    plugin = plugin_cls(fixtures.context())

    # 2. Unknown option names are rejected ------------------------------------
    def unknown_options() -> None:
        try:
            plugin.request(fixtures.result_set, __conformance_unknown__=1)
        except TypeError:
            return
        raise AssertionError("unknown option names must raise TypeError")

    check("unknown_options", unknown_options)

    # 3. Missing results fail fast --------------------------------------------
    def requires_results() -> None:
        from .errors import MissingResultsError

        if plugin_cls.requires_results:
            try:
                plugin.request(None)
            except MissingResultsError:
                return
            raise AssertionError("expected MissingResultsError for results=None")
        with fixtures.backend():
            try:
                plugin.request(None)
            except MissingResultsError as exc:
                raise AssertionError(
                    "requires_results is False but results were demanded"
                ) from exc
            except Exception:  # noqa: BLE001, S110 - a backend error is acceptable here
                pass

    check("requires_results", requires_results)

    def needs() -> None:
        from .errors import MissingResultsError

        field_for = {"concept_id": "ids", "native_id": "native_ids", "umm": "umms"}
        for need in sorted(plugin_cls.needs):
            stub = _StubResultSet()
            setattr(stub, field_for[need], [])
            if need == "umm":
                stub._umms = []
            try:
                plugin.request(stub)
            except MissingResultsError:
                continue
            raise AssertionError(f"expected MissingResultsError for missing {need!r}")

    check("needs", needs)

    # 4. A valid request returns a well-formed job ----------------------------
    job: Job | None = None

    def makes_job() -> None:
        nonlocal job
        with fixtures.backend():
            job = plugin.request(fixtures.result_set, **fixtures.options)
        assert isinstance(job, Job), "request() must return a Job"
        assert isinstance(job.id, str) and job.id, "job.id must be a non-empty string"
        assert job.plugin == plugin_cls.name, "job.plugin must match the plugin name"
        assert job.output == plugin_cls.output, "job.output must match the plugin output"
        assert isinstance(job.resumable, bool), "job.resumable must be a bool"
        assert isinstance(job.capabilities, frozenset), "job.capabilities must be a frozenset"

    check("makes_job", makes_job)

    # 5. Capabilities have matching methods -----------------------------------
    def capabilities() -> None:
        assert job is not None
        for capability in job.capabilities:
            assert callable(getattr(job, capability, None)), (
                f"capability {capability!r} has no matching method"
            )

    check("capabilities", capabilities)

    # 6. Repro of the job / resumability --------------------------------------
    def resumable() -> None:
        assert job is not None
        if job.resumable:
            rebuilt = plugin.get_job(job.id)
            assert isinstance(rebuilt, Job), "get_job() must return a Job"
            assert rebuilt.id == job.id, "get_job() must preserve the id"
        else:
            from .errors import NotSupportedError

            try:
                plugin.get_job(job.id)
            except NotSupportedError:
                return
            raise AssertionError("non-resumable plugin must raise NotSupportedError")

    check("resumable", resumable)

    # 7. wait() settles and stays settled -------------------------------------
    def settles() -> None:
        assert job is not None
        status = job.wait(timeout=120)
        assert status in _SETTLED, f"wait() returned non-terminal {status}"
        assert job.status() is status, "a settled job must stay settled"

    check("settles", settles)

    # 8. info() has no request payload; repr() is safe ------------------------
    def info_and_repr() -> None:
        assert job is not None
        info = job.info()
        assert "request" not in info, "info() must not leak the request payload"
        text = repr(job)
        assert plugin_cls.name in text and job.id in text, "repr() must identify the job"

    check("info_and_repr", info_and_repr)

    # 9. results() returns the declared output kind ---------------------------
    def results_kind() -> None:
        assert job is not None
        if job.status() not in (JobStatus.SUCCEEDED, JobStatus.PARTIAL):
            return
        value = job.results()
        assert value is not None, "results() must not return None on success"
        if job.output == "assets":
            assert isinstance(value, (list, tuple)), "assets output must be a sequence"
            for asset in value:
                assert hasattr(asset, "href"), "assets must expose an href"

    check("results_kind", results_kind)

    # 10. Failure paths raise typed errors ------------------------------------
    def failures_are_typed() -> None:
        from .errors import JobError

        if fixtures.failing_options is None:
            return
        with fixtures.backend():
            failed = plugin.request(fixtures.result_set, **fixtures.failing_options)
        status = failed.wait(timeout=120)
        if status is JobStatus.FAILED:
            try:
                failed.results()
            except JobError:
                return
            raise AssertionError("a failed job must raise a JobError from results()")
        raise AssertionError("failing_options did not produce a failed job")

    check("failures_are_typed", failures_are_typed)

    if failures:
        bullet = "\n".join(f" - {line}" for line in failures)
        raise AssertionError(f"conformance failed for {plugin_cls.__name__}:\n{bullet}")
