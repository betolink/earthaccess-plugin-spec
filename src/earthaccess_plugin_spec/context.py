"""The context handed to every plugin instance."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

__all__ = ["AuthHandle", "LazyEDLAuthHandle", "PluginContext", "default_context"]


@runtime_checkable
class AuthHandle(Protocol):
    """Lazy access to Earthdata Login credentials.

    ``session()`` returns an EDL-authenticated ``requests.Session`` and
    ``token()`` returns a bearer token. Both log in on first use, and only when
    a plugin actually asks for them.
    """

    def session(self) -> Any: ...

    def token(self) -> str: ...


class LazyEDLAuthHandle:
    """Default :class:`AuthHandle`, backed by the ``earthaccess`` library.

    ``earthaccess`` is imported inside the methods so this module (and the rest
    of the contract) can be imported without earthaccess installed. That keeps
    plugin discovery and the conformance suite dependency-free.
    """

    def _ensure_login(self) -> Any:
        import earthaccess

        auth = getattr(earthaccess, "__auth__", None)
        if auth is None or not auth.authenticated:
            earthaccess.login()
            auth = earthaccess.__auth__
        return auth

    def session(self) -> Any:
        import earthaccess

        self._ensure_login()
        return earthaccess.get_requests_https_session()

    def token(self) -> str:
        import earthaccess

        self._ensure_login()
        return earthaccess.get_edl_token()


@dataclass
class PluginContext:
    """Everything a plugin is given by the loader."""

    auth: AuthHandle
    label: str = "earthaccess"
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("earthaccess.plugins")
    )


def default_context(**kwargs: Any) -> PluginContext:
    """Build a context with the default EDL auth handle."""

    return PluginContext(auth=LazyEDLAuthHandle(), **kwargs)
