import asyncio

import pytest

from earthaccess_plugin_spec import (
    MissingResultsError,
    NotSupportedError,
    PluginBase,
    ResultSet,
    Support,
    UnsupportedCollectionError,
    as_result_set,
    list_services,
)
from earthaccess_plugin_spec.context import (
    LazyEDLAuthHandle,
    PluginContext,
    default_context,
)
from earthaccess_plugin_spec.errors import JobFailedError
from earthaccess_plugin_spec.job import Asset, Job, JobStatus
from earthaccess_plugin_spec.results import GranuleResultSet
from earthaccess_plugin_spec.support import ServiceRow, ServiceTable
from earthaccess_plugin_spec.testing import fake_context, sample_result_set

from .dummy import DummyAssetPlugin, DummyPlugin, GatedPlugin


def granule(concept_id="G1", collection_id="C1", ur="G1.EXAMPLE", umm=None):
    return {
        "meta": {"concept-id": concept_id, "collection-concept-id": collection_id},
        "umm": umm if umm is not None else {"GranuleUR": ur},
    }


class TestGranuleResultSet:
    def test_fields(self):
        rs = GranuleResultSet([granule()])
        assert rs.collection_id == "C1"
        assert rs.ids == ["G1"]
        assert rs.native_ids == ["G1.EXAMPLE"]
        assert rs.umm() == [{"GranuleUR": "G1.EXAMPLE"}]

    def test_empty(self):
        rs = GranuleResultSet([])
        assert rs.collection_id == ""
        assert rs.ids == []

    def test_multiple_collections_rejected(self):
        with pytest.raises(ValueError, match="one collection"):
            GranuleResultSet([granule(collection_id="C1"), granule(collection_id="C2")])


class TestAsResultSet:
    def test_none_passthrough(self):
        assert as_result_set(None) is None

    def test_result_set_passthrough(self):
        rs = sample_result_set()
        assert as_result_set(rs) is rs

    def test_list_wrapped(self):
        wrapped = as_result_set([granule()])
        assert isinstance(wrapped, GranuleResultSet)
        assert isinstance(wrapped, ResultSet)


class TestLocalJob:
    def test_success(self):
        plugin = DummyPlugin(fake_context())
        job = plugin.request(sample_result_set(), value=5)
        assert isinstance(job, Job)
        assert job.status() in (JobStatus.PENDING, JobStatus.RUNNING, JobStatus.SUCCEEDED)
        assert job.wait(timeout=30) is JobStatus.SUCCEEDED
        assert job.status() is JobStatus.SUCCEEDED
        assert job.results() == {"value": 5}
        assert "request" not in job.info()

    def test_failure_raises_typed_error(self):
        plugin = DummyPlugin(fake_context())
        job = plugin.request(sample_result_set(), fail=True)
        assert job.wait(timeout=30) is JobStatus.FAILED
        with pytest.raises(JobFailedError):
            job.results()

    def test_wait_timeout_does_not_raise_for_failure(self):
        plugin = DummyPlugin(fake_context())
        job = plugin.request(sample_result_set(), fail=True)
        assert job.wait(timeout=30) is JobStatus.FAILED

    def test_repr_is_identity(self):
        plugin = DummyPlugin(fake_context())
        job = plugin.request(sample_result_set())
        assert plugin.name in repr(job)
        assert job.id in repr(job)

    def test_cancel_without_capability(self):
        plugin = DummyPlugin(fake_context())
        job = plugin.request(sample_result_set())
        with pytest.raises(NotSupportedError):
            job.cancel()

    def test_run_blocks(self):
        plugin = DummyPlugin(fake_context())
        assert plugin.run(sample_result_set(), value=3) == {"value": 3}

    def test_async(self):
        plugin = DummyPlugin(fake_context())
        job = asyncio.run(plugin.arequest(sample_result_set(), value=9))
        assert asyncio.run(job.await_done(timeout=30)) is JobStatus.SUCCEEDED
        assert asyncio.run(job.aresults()) == {"value": 9}


class TestValidation:
    def test_missing_results(self):
        plugin = DummyPlugin(fake_context())
        with pytest.raises(MissingResultsError):
            plugin.request(None)

    def test_missing_need(self):
        plugin = DummyPlugin(fake_context())
        stub = sample_result_set()
        stub.ids = []  # type: ignore[attr-defined]
        with pytest.raises(MissingResultsError, match="concept_id"):
            plugin.request(stub)

    def test_unknown_option(self):
        plugin = DummyPlugin(fake_context())
        with pytest.raises(TypeError):
            plugin.request(sample_result_set(), nope=1)

    def test_get_job_not_supported(self):
        plugin = DummyPlugin(fake_context())
        with pytest.raises(NotSupportedError):
            plugin.get_job("abc")

    def test_umm_need_is_called_not_truthy_method(self):
        from earthaccess_plugin_spec import validate_inputs

        class UMMPlugin:
            name = "umm"
            needs = frozenset({"umm"})
            requires_results = True

        stub = sample_result_set()
        stub._umms = []
        with pytest.raises(MissingResultsError, match="umm"):
            validate_inputs(UMMPlugin(), stub)


class TestAssetPlugin:
    def test_assets_output(self):
        plugin = DummyAssetPlugin(fake_context())
        assets = plugin.run(sample_result_set(), count=3)
        assert len(assets) == 3
        assert all(isinstance(a, Asset) for a in assets)
        assert assets[0].access == "https"


def test_plugin_is_subclass():
    assert issubclass(DummyPlugin, PluginBase)


def test_default_context_uses_lazy_edl_handle():
    ctx = default_context()
    assert isinstance(ctx, PluginContext)
    assert isinstance(ctx.auth, LazyEDLAuthHandle)
    assert ctx.label == "earthaccess"


class TestSupport:
    def test_default_is_supported(self):
        assert DummyPlugin(fake_context()).supports(sample_result_set()) == Support(True)

    def test_unsupported_raises_before_request(self):
        plugin = GatedPlugin(fake_context())
        results = sample_result_set(collection_id="C-OTHER")
        with pytest.raises(UnsupportedCollectionError) as excinfo:
            plugin.request(results)
        assert "does not support" in str(excinfo.value)
        assert excinfo.value.collection_id == "C-OTHER"

    def test_check_false_bypasses(self):
        plugin = GatedPlugin(fake_context())
        results = sample_result_set(collection_id="C-OTHER")
        job = plugin.request(results, check=False)
        assert job.results() == "ok"

    def test_supports_is_cached_per_collection(self):
        plugin = GatedPlugin(fake_context())
        results = sample_result_set(collection_id="C1")
        assert plugin.supports(results).ok is True
        assert plugin.supports(results).ok is True
        assert plugin.checks == 1

    def test_check_is_reserved(self):
        from dataclasses import dataclass

        with pytest.raises(TypeError, match="reserved"):

            @dataclass
            class BadOptions:
                check: bool = False

            class BadPlugin(PluginBase):
                name = "bad"
                auth = "none"
                output = "dataframe"
                Options = BadOptions

                def _request(self, results, options):
                    return self.job(lambda: None)


class TestGranuleResultSetExtras:
    def test_short_name_and_version(self):
        g = granule(umm={"GranuleUR": "G1", "CollectionReference": {"ShortName": "ATL06", "Version": "006"}})
        rs = GranuleResultSet([g])
        assert rs.short_name == "ATL06"
        assert rs.version == "006"

    def test_is_a_list(self):
        rs = GranuleResultSet([granule()])
        assert isinstance(rs, list)
        assert len(rs) == 1

    def test_slice_preserves_type_and_services(self):
        rs = GranuleResultSet(
            [granule(concept_id="g1"), granule(concept_id="g2")],
            services=[{"Type": "Harmony", "Name": "svc"}],
        )
        sliced = rs[:1]
        assert isinstance(sliced, GranuleResultSet)
        assert len(sliced) == 1
        assert sliced.services() == [{"Type": "Harmony", "Name": "svc"}]


class TestListServices:
    def test_table_renders(self):
        table = ServiceTable(
            [ServiceRow("harmony", False, "no service"), ServiceRow("sliderule", True)]
        )
        text = repr(table)
        assert "plugin" in text and "harmony" in text and "sliderule" in text
        assert table.accepting() == ["sliderule"]

    def test_list_services_queries_installed(self, monkeypatch):
        from earthaccess_plugin_spec import discovery

        monkeypatch.setattr(
            discovery, "installed_plugins", lambda group=None: {"gated": GatedPlugin}
        )
        table = list_services(sample_result_set(collection_id="C1"))
        assert [row.plugin for row in table] == ["gated"]
        assert table.rows[0].supported is True

    def test_result_set_list_services(self, monkeypatch):
        from earthaccess_plugin_spec import discovery

        monkeypatch.setattr(
            discovery, "installed_plugins", lambda group=None: {"gated": GatedPlugin}
        )
        rs = GranuleResultSet([granule(collection_id="C1")])
        table = rs.list_services()
        assert [row.plugin for row in table] == ["gated"]
        assert table.rows[0].supported is True
