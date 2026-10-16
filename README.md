# earthaccess-plugin-spec

The contract that every [`earthaccess`](https://github.com/earthaccess-dev/earthaccess)
plugin follows, plus a cookiecutter template and a conformance suite.

`earthaccess` discovers plugins through the `earthaccess.plugins` entry-point
group and drives them through two classes:

- **`PluginBase` — always subclass it.** Declare `Options` (a dataclass) and
  implement `_request()`.
- **`Job` — subclass it only for a remote backend you poll.** Override
  `_poll()` / `_fetch()` / `_cancel()`.

In one line: subclass `PluginBase` always; return `self.job(fn)` for local work,
and subclass `Job` only when you poll a remote backend.

## Install

```bash
pip install earthaccess-plugin-spec
# or, to use the default Earthdata Login auth handle:
pip install "earthaccess-plugin-spec[edl]"
```

## Write a plugin

```python
from dataclasses import dataclass
from earthaccess_plugin_spec import Asset, PluginBase


class MyPlugin(PluginBase):
    name = "myplugin"
    needs = frozenset({"concept_id"})
    auth = "edl"          # 'edl' | 'own' | 'none'
    output = "assets"     # 'assets' | 'xarray' | 'dataframe'

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

`request(results, **options)` validates the inputs, runs `_supports()`, calls
`_request()`, and returns a `Job` immediately.

## The Job

However the backend behaves, the caller drives it the same way:

```python
job = ea.plugins.myplugin.request(results, ...)

job.status()          # PENDING | RUNNING | PAUSED | SUCCEEDED | PARTIAL | FAILED | CANCELED
job.info()            # backend detail (a dict); never the request payload
job.results()         # blocks until settled, then returns the output (or raises)
job.wait(timeout=60)  # wait without fetching; returns the final status
repr(job)             # never makes a network call

# async mirrors: await job.astatus() / job.await_done() / job.aresults()
```

There are three shapes to choose from:

| Shape | How | Example |
| --- | --- | --- |
| **A value in hand** | `return self.job(fn)` where `fn` returns at once | PyDAP builds OPeNDAP URLs |
| **Local compute** | `return self.job(fn)` where `fn` does the work | SlideRule processing |
| **Remote, polled** | subclass `Job`, override `_poll` / `_fetch` / `_cancel` | Harmony |

For the first two, `self.job(fn)` runs `fn` in a background thread and the job
completes on its own — a value in hand is just a function that returns
immediately, and a local compute job is one that takes a while. `status()` is
`PENDING`/`RUNNING` until it settles. Only a remote backend needs a `Job`
subclass (see below).

### When the job is done

`output` tells earthaccess how to treat `results()`:

| `output` | `results()` returns | `ea.open(job)` / `ea.download(job, path)` |
| --- | --- | --- |
| `assets` | `list[Asset]` (files) | opened / downloaded by earthaccess |
| `xarray`, `dataframe`, ... | whatever the plugin deems correct | `ea.open` returns it as-is; `download` is not supported |

So if your job yields assets, users can `ea.open(job)` or `ea.download(job, path)`.
For anything else, `results()` returns whatever makes sense for your backend — a
lazy `xarray.Dataset`, a `GeoDataFrame`, native PyDAP datasets or OPeNDAP URLs,
and so on — and earthaccess hands it straight back.

### The rules

- `needs` is **checked, not fetched**: `search_data()` already returns full UMM.
- `request()` returns a `Job` immediately; `results()` blocks and returns the output.
- Import your backend **inside methods**, never at module level, so discovery stays cheap.
- Subclass `Job` **only** for a remote backend.
- Override `_supports()` (returns a `Capabilities`) to report what a collection
  supports. A definite `Capabilities(False, reason=...)` makes `request()` raise
  `UnsupportedCollectionError`; `None` ("could not tell") only warns. Users can
  bypass it with `request(results, check=False)`, ask directly with
  `plugin.supports(results)` / `plugin.capabilities("ATL06")`, or list every
  plugin's answer with `results.list_services()`.

## Remote backends (subclass `Job`)

Only a backend you poll needs this. Override the three hooks and set the class
attributes:

```python
from earthaccess_plugin_spec import Job, JobStatus, PluginBase


class MyJob(Job):
    resumable = True                      # plugin.get_job(id) can rebuild it
    capabilities = frozenset({"cancel"})  # a string means the method exists
    poll_every = 2.0                      # seconds between polls

    def __init__(self, job_id, client):
        super().__init__(plugin="myplugin", output="assets", id=job_id)
        self._client = client

    def _poll(self):                      # one call -> (status, info)
        info = self._client.status(self.id)
        info.pop("request", None)         # never expose the payload
        raw = info.get("status")
        return {
            "queued": JobStatus.PENDING,
            "running": JobStatus.RUNNING,
            "done": JobStatus.SUCCEEDED,
        }.get(raw, JobStatus.RUNNING), info

    def _fetch(self):                     # output of a settled job
        return [Asset(href=u, access="s3") for u in self._client.result_urls(self.id)]

    def _cancel(self):
        self._client.cancel(self.id)
        return True
```

In the plugin, submit and return it, and implement `get_job` for `resumable=True`:

```python
class MyPlugin(PluginBase):
    ...
    def _request(self, results, options):
        client = ...                      # import your backend inside the method
        return MyJob(client.submit(...), client)

    def get_job(self, job_id):
        return MyJob(job_id, ...)
```

## Documentation

The [docs hub](docs/index.md) explains the plugin system, the collection-support
model, and has a guide per plugin:

- [Plugin overview](docs/index.md)
- [harmony](docs/plugins/harmony.md) · [pydap](docs/plugins/pydap.md) · [sliderule](docs/plugins/sliderule.md)

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
mode. The generated project has a working `PluginBase` subclass, an optional
`Job` subclass (remote only), a conformance test, and CI.

## Import name

The distribution is `earthaccess-plugin-spec`; the import package is
`earthaccess_plugin_spec`.

## License

MIT.
