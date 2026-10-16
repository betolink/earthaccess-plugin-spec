# earthaccess-plugin-spec

The contract that every [`earthaccess`](https://github.com/earthaccess-dev/earthaccess)
plugin follows, plus a cookiecutter template and a conformance suite.

`earthaccess` discovers plugins through the `earthaccess.plugins` entry-point
group and drives them through the two classes defined here:

- **`PluginBase`** — subclass this. Declare `Options` (a dataclass) and implement
  `_request()`.
- **`Job`** — one concrete class. Local work is `self.job(fn)`. Subclass it only
  when you poll a remote backend (for example Harmony).

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

### The rules

- `needs` is **checked, not fetched**. `search_data()` already returns full UMM.
- `request()` returns a `Job` immediately. `results()` blocks. `run()` is
  `request().results()`.
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
