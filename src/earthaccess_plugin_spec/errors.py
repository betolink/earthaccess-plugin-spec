"""Typed errors raised by the earthaccess plugin contract."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .job import JobStatus

__all__ = [
    "EarthaccessPluginError",
    "JobCanceledError",
    "JobError",
    "JobFailedError",
    "JobPausedError",
    "MissingResultsError",
    "NotSupportedError",
    "PluginLoadError",
    "PluginNotFoundError",
    "UnsupportedOutputError",
]


class EarthaccessPluginError(Exception):
    """Base class for every error raised by the plugin contract."""


class PluginNotFoundError(EarthaccessPluginError, AttributeError):
    """Raised when a plugin is not installed.

    It also derives from :class:`AttributeError` so the ``earthaccess.plugins``
    namespace can translate it into a failed attribute lookup.
    """


class PluginLoadError(EarthaccessPluginError):
    """Raised when an installed plugin fails to import or targets another contract."""


class MissingResultsError(EarthaccessPluginError):
    """Raised when the supplied results do not satisfy a plugin's requirements."""


class NotSupportedError(EarthaccessPluginError):
    """Raised when a plugin or job does not support an operation."""


class UnsupportedOutputError(EarthaccessPluginError):
    """Raised when a job's output kind cannot feed a requested operation."""


class JobError(EarthaccessPluginError):
    """Base class for job state errors. Carries the job id and status."""

    def __init__(
        self,
        job_id: str,
        status: JobStatus | None = None,
        detail: Any = None,
    ) -> None:
        self.job_id = job_id
        self.status = status
        self.detail = detail
        super().__init__(self._message())

    def _message(self) -> str:
        return f"job {self.job_id} is in an error state"


class JobFailedError(JobError):
    """Raised by ``Job.results()`` when the job failed."""

    def __init__(self, job_id: str, info: Mapping[str, Any] | None = None) -> None:
        self.info = dict(info or {})
        super().__init__(job_id, status=None, detail=self.info)

    def _message(self) -> str:
        error = self.info.get("error")
        return f"job {self.job_id} failed" + (f": {error}" if error else "")


class JobCanceledError(JobError):
    """Raised by ``Job.results()`` when the job was canceled."""

    def __init__(self, job_id: str) -> None:
        super().__init__(job_id)

    def _message(self) -> str:
        return f"job {self.job_id} was canceled"


class JobPausedError(JobError):
    """Raised by ``Job.results()`` when the job is paused (for example a preview gate).

    The message tells the caller how to move forward.
    """

    def __init__(self, job_id: str) -> None:
        super().__init__(job_id)

    def _message(self) -> str:
        return (
            f"job {self.job_id} is paused; call resume() to continue or "
            "skip_preview() to accept the preview"
        )
