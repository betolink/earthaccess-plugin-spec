"""The earthaccess plugin contract.

Plugin authors subclass :class:`~earthaccess_plugin_spec.PluginBase`, declare an
``Options`` dataclass, and implement ``_request``. Remote backends also subclass
:class:`~earthaccess_plugin_spec.Job`.

Run the conformance suite from ``earthaccess_plugin_spec.testing`` in CI.
"""

from __future__ import annotations

from .base import PluginBase, validate_inputs
from .context import AuthHandle, LazyEDLAuthHandle, PluginContext, default_context
from .errors import (
    EarthaccessPluginError,
    JobCanceledError,
    JobError,
    JobFailedError,
    JobPausedError,
    MissingResultsError,
    NotSupportedError,
    PluginLoadError,
    PluginNotFoundError,
    UnsupportedOutputError,
)
from .job import Asset, Job, JobStatus
from .results import GranuleResultSet, ResultSet, as_result_set

CONTRACT_VERSION = 1

__all__ = [
    "CONTRACT_VERSION",
    "Asset",
    "AuthHandle",
    "EarthaccessPluginError",
    "GranuleResultSet",
    "Job",
    "JobCanceledError",
    "JobError",
    "JobFailedError",
    "JobPausedError",
    "JobStatus",
    "LazyEDLAuthHandle",
    "MissingResultsError",
    "NotSupportedError",
    "PluginBase",
    "PluginContext",
    "PluginLoadError",
    "PluginNotFoundError",
    "ResultSet",
    "UnsupportedOutputError",
    "as_result_set",
    "default_context",
    "validate_inputs",
]
