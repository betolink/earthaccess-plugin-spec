# SlideRule

`ea.plugins.sliderule` — on-demand processing of ICESat-2 and GEDI data with
[SlideRule](https://slideruleearth.io/).

SlideRule is a cloud platform for satellite altimetry and lidar. Instead of
downloading raw ATL03/ATL06/ATL08 or GEDI granules, you send a processing
request — an API such as `atl06p`, `atl03p`, `atl08p` or a GEDI processor, plus
parameters and a region of interest — and it runs the analysis server-side,
returning geolocated point data.

```python
import earthaccess as ea

ea.plugins.sliderule.configure(url="https://slideruleearth.io", organization="my-org")

results = ea.search_data(short_name="ATL06", bounding_box=(-120, 40, -110, 45))
df = ea.plugins.sliderule.request(
    results,
    api="atl06p",
    parms={"pass_invalid": False},
    aoi={"type": "Polygon", "coordinates": [[[...]]]},
).results()
```

The searched granules scope the request; you can also run from `aoi` + `parms`
alone with no search results.

**Options:** `api` (required), `parms`, `aoi`, `resources`.
**Output:** `GeoDataFrame`.
**Auth:** SlideRule manages its own credentials (use `configure()`).

Full guide and examples: [`earthaccess-plugin-sliderule/README.md`](https://github.com/betolink/earthaccess-plugin-sliderule).
