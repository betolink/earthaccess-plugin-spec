# earthaccess-plugin-spec

The contract that every [`earthaccess`](https://github.com/earthaccess-dev/earthaccess)
plugin follows, plus a cookiecutter template and a conformance suite.

`earthaccess` discovers plugins through the `earthaccess.plugins` entry-point
group and drives them through the two classes defined here. A plugin author
writes:

- **a `PluginBase` subclass — always.** Declare `Options` (a dataclass) and
  implement `_request()`. Local work is `self.job(fn)`.
- **a `Job` subclass — only for a remote backend** that you poll. Override
  `_poll()`, `_fetch()` and (if you can cancel) `_cancel()`, and set
  `resumable` / `capabilities` / `poll_every`.

Both are re-exported from `earthaccess_plugin_spec`. The rule in one line:
subclass `PluginBase` always; subclass `Job` only when you poll a remote backend,
otherwise return `self.job(fn)`.

The full rationale lives in the earthaccess plugin plan. This package is the
executable version of that contract.

## Install

```bash
pip install earthaccess-plugin-spec
# or, to use the default Earthdata Login auth handle:
pip install "earthaccess-plugin-spec[edl]"
```

## Write a plugin

```python
from dataclasses import dataclass, field
from earthaccess_plugin_spec import Asset, PluginBase


class MyPlugin(PluginBase):
    name = "myplugin"
    needs = frozenset({"concept_id"})
    auth = "edl"
    output = "assets"

    @dataclass
    class Options:
        format: str = "netcdf4"

    def _request(self, results, options):
        # import your backend inside the method, never at module level
        return self.job(lambda: [Asset(href="s3://...", access="s3")])
```

Register it:

```toml
[project.entry-points."earthaccess.plugins"]
myplugin = "earthaccess_myplugin:MyPlugin"
```

### Remote backends: subclass `Job`

If your backend runs asynchronously and you have to poll it (like Harmony), you
also subclass `Job` and override the three hooks. A local job never needs this.

```python
from earthaccess_plugin_spec import Job, JobStatus, PluginBase


class MyJob(Job):
    resumable = True                              # plugin.get_job(id) rebuilds it
    capabilities = frozenset({"cancel"})          # a string means the method exists
    poll_every = 2.0                              # seconds between polls

    def __init__(self, job_id, client):
        super().__init__(plugin="myplugin", output="assets", id=job_id)
        self._client = client

    def _poll(self):                              # one call -> (status, info)
        info = self._client.status(self.id)
        info.pop("request", None)                 # never expose the payload
        return {"queued": JobStatus.PENDING,
                "running": JobStatus.RUNNING,
                "done": JobStatus.SUCCEEDED}.get(info.get("status"), JobStatus.RUNNING), info

    def _fetch(self):                             # output of a settled job
        return [Asset(href=url, access="s3") for url in self._client.result_urls(self.id)]

    def _cancel(self):
        self._client.cancel(self.id)
        return True


class MyPlugin(PluginBase):
    name = "myplugin"
    needs = frozenset({"concept_id"})
    auth = "edl"
    output = "assets"

    @dataclass
    class Options:
        format: str = "netcdf4"

    def _request(self, results, options):
        client = ...                              # import your backend inside the method
        return MyJob(client.submit(...), client)

    def get_job(self, job_id):
        return MyJob(job_id, ...)                 # resumable=True requires this
```

### The rules

- `needs` is **checked, not fetched**. `search_data()` already returns full UMM.
- `request()` returns a `Job` immediately. `results()` blocks and returns the
  plugin's output.
- Import your backend **inside methods**, never at module level, so plugin
  discovery stays cheap.
- Only override `Job._poll` / `_fetch` / `_cancel` for a remote backend.
- Override `_supports()` (returns a `Capabilities`) to report what a collection
  supports. A definite `Capabilities(False, reason=...)` makes `request()` raise
  `UnsupportedCollectionError` before any backend call. It is tri-state, so a
  `None` ("could not tell") only warns. Users can bypass it with
  `request(results, check=False)`, ask a plugin directly with
  `plugin.supports(results)` / `plugin.capabilities("ATL06")`, or list every
  plugin's answer with `results.list_services()`.

## Documentation

The [docs hub](docs/index.md) explains the plugin system, the collection-support
model, and has a guide and notebook per plugin:

- [Plugin overview](docs/index.md)
- [harmony](docs/plugins/harmony.md) · [pydap](docs/plugins/pydap.md) · [sliderule](docs/plugins/sliderule.md)
- [Walkthrough notebook](docs/notebooks/plugins_overview.ipynb)

## Conformance suite

Run the contract checks in your own test suite:

```python
from earthaccess_plugin_spec.testing import Fixtures, run_conformance

from earthaccess_myplugin import MyPlugin


class MyFixtures(Fixtures):
    def backend(self):
        return patch_my_backend()  # a context manager


def test_conformance():
    run_conformance(MyPlugin, fixtures=MyFixtures(options={"format": "zarr"}))
```

`run_conformance` fails with a list of every check that did not pass.

## Cookiecutter template

Scaffold a new plugin repository:

```bash
cookiecutter gh:betolink/earthaccess-plugin-spec --directory template
```

You will be asked for the plugin name, backend package, output kind and auth
mode. The generated project has a working `PluginBase` subclass, a conformance
test, and CI.

## Import name

The distribution is `earthaccess-plugin-spec`; the import package is
`earthaccess_plugin_spec`.

## License

MIT.
