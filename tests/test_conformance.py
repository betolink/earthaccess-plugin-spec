import pytest

from earthaccess_plugin_spec import PluginBase
from earthaccess_plugin_spec.testing import Fixtures, run_conformance

from .dummy import DummyAssetPlugin, DummyPlugin


def test_dummy_plugin_conforms():
    run_conformance(
        DummyPlugin,
        fixtures=Fixtures(options={"value": 7}, failing_options={"fail": True}),
    )


def test_dummy_asset_plugin_conforms():
    run_conformance(DummyAssetPlugin, fixtures=Fixtures(options={"count": 2}))


class BrokenPlugin(PluginBase):
    name = "broken"
    auth = "none"
    output = "dataframe"
    Options = DummyPlugin.Options

    def _request(self, results, options):
        return "not a job"


def test_conformance_detects_broken_plugin():
    with pytest.raises(AssertionError, match="conformance failed"):
        run_conformance(BrokenPlugin, fixtures=Fixtures())
