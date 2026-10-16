# PyDAP

`ea.plugins.pydap` — OPeNDAP access to Earthdata granules through
[PyDAP](https://www.pydap.org/) and xarray.

OPeNDAP (DAP2/DAP4) lets you read parts of a remote dataset without downloading
whole files: the server serves the slices you ask for. The plugin is a
**request** that returns a completed job; it does not open the data itself,
because that needs xarray kwargs tuned to the dataset.

```python
import earthaccess as ea
import xarray as xr

results = ea.search_data(short_name="MUR-JPL-L4-GLOB-v4.1", ...)

# Inspect a granule's variables with the native client.
ea.plugins.pydap.request(results, client="pydap").results()[0].tree()

# Ask for those variables: ea.open(job) returns the OPeNDAP DAP4 URLs with the
# ?dap4.ce=... constraint.
job = ea.plugins.pydap.request(results, variables=["analysed_sst", "lat"])
urls = ea.open(job)

session = ea.get_requests_https_session()
ds = xr.open_mfdataset(urls, engine="pydap", session=session, combine="nested",
                       concat_dim="time", parallel=True, chunks={"lat": 400, "lon": 400})

# or write the constrained data to local NetCDF:
# ea.download(job, "./data")
```

**Options:** `client` (`xarray` -> asset URLs / `pydap` -> native datasets),
`protocol` (`dap4`/`dap2`), `variables` (DAP4 constraint), `url_filter`.
**Output:** OPeNDAP asset URLs with a variable constraint, or native pydap
datasets. `ea.open(job)` returns the URLs; `ea.download(job, path)` serializes
them to local NetCDF; `ea.virtualize` does not apply.
**Auth:** Earthdata Login (the plugin uses your EDL session).

Full guide and examples: [`earthaccess-plugin-pydap/README.md`](https://github.com/betolink/earthaccess-plugin-pydap).
