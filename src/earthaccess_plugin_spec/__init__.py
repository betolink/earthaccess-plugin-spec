"""The earthaccess plugin contract.

Plugin authors subclass :class:`~earthaccess_plugin_spec.PluginBase`, declare an
``Options`` dataclass, and implement ``_request``. Remote backends also subclass
:class:`~earthaccess_plugin_spec.Job`. Override ``_supports`` to reject
collections the plugin cannot handle.

Run the conformance suite from ``earthaccess_plugin_spec.testing`` in CI.
"""

from __future__ import annotations

from .base import PluginBase, accepting_plugins, validate_inputs
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
    UnsupportedCollectionError,
    UnsupportedOutputError,
)
from .job import Asset, Job, JobStatus
from .results import GranuleResultSet, ResultSet, as_result_set, list_services
from .support import Capabilities, Capability, ServiceRow, ServiceTable, Support
from .version import CONTRACT_VERSION

__all__ = [
    "CONTRACT_VERSION",
    "Asset",
    "AuthHandle",
    "Capabilities",
    "Capability",
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
    "ServiceRow",
    "ServiceTable",
    "Support",
    "UnsupportedCollectionError",
    "UnsupportedOutputError",
    "accepting_plugins",
    "as_result_set",
    "as_target",
    "default_context",
    "list_services",
    "validate_inputs",
]
