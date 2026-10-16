# Harmony

`ea.plugins.harmony` — subset, reproject, reformat and transform Earthdata
granules with [NASA Harmony](https://harmony.earthdata.nasa.gov/).

Harmony is NASA's asynchronous, cloud-based transformation service. Send it a
collection, a set of granules, a region and a transformation chain (`subset`,
`reproject`, `concatenate`, ...), and it runs the work in the cloud. Large
requests can be held in a **preview** state for approval.

```python
import earthaccess as ea

results = ea.search_data(short_name="ATL06", bounding_box=(-120, 40, -110, 45))
job = ea.plugins.harmony.request(results, variables=["/gt1l/land_ice_segments/h_li"])

dataset = ea.open(job)          # or ea.download(job, "./data")
```

Harmony is the reference **remote, resumable** job. In addition to
`status()` / `info()` / `results()`, you can steer an order:

```python
job.pause(); job.resume(); job.skip_preview(); job.cancel()
same = ea.plugins.harmony.get_job(job.id)   # resume from another process
```

A large request maps to `JobStatus.PAUSED`; `results()` then raises
`JobPausedError` and tells you to `skip_preview()` or `resume()`.

**Options:** `bbox`, `variables`, `shapefile`, `output_format`, `skip_preview`.
**Output:** `list[Asset]` (`ea.open` / `ea.download` accept the job).
**Auth:** Earthdata Login.

Full guide and examples: [`earthaccess-plugin-harmony/README.md`](https://github.com/betolink/earthaccess-plugin-harmony).
