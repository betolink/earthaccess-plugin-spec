"""A minimal plugin used to exercise the contract and the conformance suite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from earthaccess_plugin_spec import Asset, PluginBase


@dataclass
class Options:
    value: int = 1
    fail: bool = False


class DummyPlugin(PluginBase):
    name = "dummy"
    needs = frozenset({"concept_id"})
    auth = "none"
    output = "dataframe"
    Options = Options

    def _request(self, results: Any, options: Any) -> Any:
        def work() -> dict[str, int]:
            if options.fail:
                raise RuntimeError("boom")
            return {"value": options.value}

        return self.job(work)


@dataclass
class AssetOptions:
    count: int = 1


class DummyAssetPlugin(PluginBase):
    name = "dummy-assets"
    needs = frozenset({"concept_id"})
    auth = "none"
    output = "assets"
    Options = AssetOptions

    def _request(self, results: Any, options: AssetOptions) -> Any:
        def work() -> list[Asset]:
            return [
                Asset(href=f"https://example.org/{i}.nc4", access="https")
                for i in range(options.count)
            ]

        return self.job(work)
