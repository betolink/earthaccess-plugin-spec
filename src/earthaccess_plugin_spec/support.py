"""Collection-support reporting: ``Support`` and the ``list_services`` table."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["ServiceRow", "ServiceTable", "Support"]


@dataclass(frozen=True)
class Support:
    """The result of a plugin's cheap, collection-level support check.

    ``ok`` is tri-state on purpose: service associations and capabilities can
    lag reality, so ``None`` ("could not tell") must never hard-block a request
    the service might accept. Only a definite ``False`` raises.
    """

    ok: bool | None
    reason: str = ""


@dataclass(frozen=True)
class ServiceRow:
    """One plugin's answer in the ``list_services`` table."""

    plugin: str
    supported: bool | None
    detail: str = ""

    @property
    def _label(self) -> str:
        return {True: "yes", False: "no", None: "?"}[self.supported]


@dataclass
class ServiceTable:
    """A printable table of which installed plugins accept some results."""

    rows: list[ServiceRow] = field(default_factory=list)

    def __iter__(self) -> Any:
        return iter(self.rows)

    def __len__(self) -> int:
        return len(self.rows)

    def accepting(self) -> list[str]:
        return [row.plugin for row in self.rows if row.supported is True]

    def _render(self) -> str:
        header = ("plugin", "supported", "detail")
        body = [(row.plugin, row._label, row.detail) for row in self.rows]
        widths = [len(col) for col in header]
        for row in body:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))
        lines = [
            "  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(header)).rstrip(),
            "  ".join("-" * widths[i] for i in range(len(header))),
        ]
        for row in body:
            lines.append(
                "  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)).rstrip()
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self._render()

    def __str__(self) -> str:
        return self._render()

    def _repr_html_(self) -> str:
        head = "<tr><th>plugin</th><th>supported</th><th>detail</th></tr>"
        body = "".join(
            f"<tr><td>{row.plugin}</td><td>{row._label}</td><td>{row.detail}</td></tr>"
            for row in self.rows
        )
        return f"<table>{head}{body}</table>"
