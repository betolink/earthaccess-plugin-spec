# PyDAP

`ea.plugins.pydap` — lazy [OPeNDAP](https://www.opendap.org/) access to
Earthdata granules through [PyDAP](https://www.pydap.org/) and xarray.

OPeNDAP (DAP2/DAP4) lets you read parts of a remote dataset without downloading
whole files: the server serves the slices you ask for. PyDAP is the Python
client, and xarray opens PyDAP responses with `engine="pydap"`, giving a lazy
`xarray.Dataset` that fetches data on demand.

```python
import earthaccess as ea

results = ea.search_data(short_name="MODISA_L2_OC", ...)
ds = ea.plugins.pydap.open(results, protocol="dap4")   # lazy xarray.Dataset
subset = ds["chlor_a"].sel(lat=slice(40, 50)).mean()
```

The result is already a usable object, so `ea.open(job)` returns it as-is;
nothing is downloaded until you compute with it.

A single granule is kept lazy so the subset is pushed to the server; for several
granules pass `chunks` sized to your subset. To navigate the remote file
instead, ask for the native pydap dataset:

```python
ea.plugins.pydap.run(results, engine="pydap").tree()   # one per granule URL
```

**Options:** `engine` (`xarray`/`pydap`), `protocol` (`dap4`/`dap2`),
`url_filter`, `combine` (`by_coords`/`nested`), `concat_dim`, `chunks`.
**Output:** lazy `xarray.Dataset` (or native pydap dataset with `engine="pydap"`).
**Auth:** Earthdata Login (the plugin uses your EDL session).

Full guide and examples: [`earthaccess-plugin-pydap/README.md`](https://github.com/betolink/earthaccess-plugin-pydap).
