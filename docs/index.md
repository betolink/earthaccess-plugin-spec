# earthaccess plugins

earthaccess plugins let you reach services that are not part of `earthaccess`
itself without growing the core library. Each plugin is a small, independently
installable package that implements one remote or local backend and registers
itself with earthaccess.

```bash
pip install earthaccess-plugin-harmony   # or -pydap, -sliderule
```

Once installed, a plugin appears under `ea.plugins`:

```python
import earthaccess as ea

ea.list_plugins()                 # table of installed plugins
results = ea.search_data(short_name="ATL06", ...)
job = ea.plugins.harmony.request(results, variables=["/gt1l/land_ice_segments/h_li"])
assets = ea.open(job)             # or ea.download(job, "./data")
```

## The plugins

| Plugin | Upstream service | Returns | Auth | Job |
| --- | --- | --- | --- | --- |
| [harmony](plugins/harmony.md) | NASA Harmony | `list[Asset]` | Earthdata Login | remote, resumable |
| [pydap](plugins/pydap.md) | OPeNDAP via PyDAP | lazy `xarray.Dataset` | Earthdata Login | local |
| [sliderule](plugins/sliderule.md) | SlideRule | `GeoDataFrame` | its own | local |

## The contract in one screen

Plugins are written against two classes from
[`earthaccess-plugin-spec`](https://github.com/betolink/earthaccess-plugin-spec):

- **`PluginBase`** — subclass it, declare `Options` (a dataclass) and implement
  `_request()`. Optionally override `_supports()` to reject datasets you cannot
  handle.
- **`Job`** — one class for both modes. Local work is `self.job(fn)`; a remote
  backend subclasses `Job` and overrides `_poll` / `_fetch` / `_cancel`.

Every request follows the same shape regardless of backend:

```python
job = ea.plugins.<name>.request(results, **options)   # returns immediately
job.status()       # PENDING / RUNNING / PAUSED / SUCCEEDED / PARTIAL / FAILED / CANCELED
job.info()         # backend detail; never the request payload
job.results()      # blocks, returns the plugin's output
ea.plugins.<name>.run(results, **options)             # request(...).results()
```

## Collection support validation

Passing results a plugin cannot handle fails early, before any backend call.
Each plugin implements a cheap, collection-level `_supports()` check:

| Plugin | Evidence it uses | Network |
| --- | --- | --- |
| harmony | UMM-S service association, then the capabilities endpoint | one cached call |
| pydap | OPeNDAP links already in the granule UMM | none |
| sliderule | a hardcoded allowlist of dataset short names | none |

```python
>>> results.list_services()
plugin     supported  detail
--------   ---------  ------
harmony    no         no Harmony service is associated with C1234567890-NSIDC_CPRD
pydap      yes
sliderule  yes

>>> ea.plugins.harmony.request(results, variables=["h_li"])
UnsupportedCollectionError: harmony does not support ATL06 (C1234567890-NSIDC_CPRD):
no Harmony service is associated with that collection.
Plugins that accept these results: sliderule, pydap. See results.list_services().
```

The answer is tri-state: `True` (yes), `False` (definitively no) and `None`
("could not tell"). Only a definite `False` raises, because service
associations and capabilities can lag reality. `request(results, check=False)`
skips the check for a dataset you know the service accepts.

## Walkthrough notebook

See [notebooks/plugins_overview.ipynb](notebooks/plugins_overview.ipynb) for a
runnable tour with an example per plugin.

## Writing your own plugin

```bash
cookiecutter gh:betolink/earthaccess-plugin-spec --directory template
```

The generated project has a working `PluginBase`, an optional `_supports`, a
conformance test and CI. See the [spec repository](https://github.com/betolink/earthaccess-plugin-spec)
for the full contract and the conformance suite.

> **Status:** the plugin registry (`ea.plugins`, `ea.list_plugins`,
> `ea.open`/`ea.download` dispatch) is the next core milestone. Until it lands,
> the examples above describe the intended API; the plugins and their
> conformance tests already implement it.
