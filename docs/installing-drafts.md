# Installing the current drafts

> **Pre-release.** `earthaccess-plugin-spec` and the plugins are **not on PyPI
> yet**. Install them straight from GitHub for now. Once they are published, this
> page is replaced by plain `pip install earthaccess-plugin-<name>`.

You install four things: the **contract** (`earthaccess-plugin-spec`) and three
**plugins** (`earthaccess-plugin-harmony`, `-pydap`, `-sliderule`). They are only
useful together with the plugins-enabled `earthaccess` branch, `plugin-spec`.

## Prerequisites

- Python ≥ 3.12 and `git`
- An Earthdata Login account (`ea.login()` reads `~/.netrc`, or set
  `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD`)
- For SlideRule: an account/organization at <https://slideruleearth.io>

## With uv (recommended)

`uv` reads each plugin's `[tool.uv.sources]`, so the contract is pulled from
GitHub automatically.

```bash
# 1. the plugins-enabled earthaccess branch
git clone git@github.com:betolink/earthaccess.git
cd earthaccess
git checkout plugin-spec

# 2. environment + earthaccess with all optional deps
uv venv
uv pip install -e ".[all]"          # or: -e . plus the deps you need

# 3. the contract and the plugins, from GitHub
uv pip install "git+https://github.com/betolink/earthaccess-plugin-spec.git"
uv pip install "git+https://github.com/betolink/earthaccess-plugin-harmony.git"
uv pip install "git+https://github.com/betolink/earthaccess-plugin-pydap.git"
uv pip install "git+https://github.com/betolink/earthaccess-plugin-sliderule.git"

# 4. notebook deps and the NetCDF stack
uv pip install jupyterlab matplotlib "h5netcdf>=1.7" netCDF4

# 5. sanity check
uv run python -c "import earthaccess as ea; ea.list_plugins()"

# 6. run the examples
source .venv/bin/activate
jupyter lab docs/tutorials/plugins/
```

## With pip

`pip` ignores `tool.uv.sources`, so install the contract **first** (otherwise its
dependency can't be resolved — it is not on PyPI).

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip

# contract first
pip install "git+https://github.com/betolink/earthaccess-plugin-spec.git"

pip install -e ".[all]"             # the plugin-spec earthaccess branch
pip install "git+https://github.com/betolink/earthaccess-plugin-harmony.git"
pip install "git+https://github.com/betolink/earthaccess-plugin-pydap.git"
pip install "git+https://github.com/betolink/earthaccess-plugin-sliderule.git"

pip install jupyterlab matplotlib "h5netcdf>=1.7" netCDF4
jupyter lab docs/tutorials/plugins/
```

## A lighter install

`.[all]` is heavy (rasterio, virtualizarr, icechunk, odc-stac, dask, ...). For
just the plugin notebooks:

```bash
uv pip install -e .
uv pip install xarray geopandas matplotlib jupyterlab "h5netcdf>=1.7" netCDF4
```

## Notes

- **Credentials.** `ea.login()` reads `~/.netrc`; otherwise export
  `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD` and call
  `ea.login(strategy="environment")`.
- **`h5netcdf>=1.7`.** Older `h5netcdf` is incompatible with `h5py` 3.16 and
  fails when reading the Harmony NetCDF output.
- **`netCDF4`.** Only needed for the PyDAP `ea.download(...)` example (pydap
  streaming output).
- **SlideRule.** Set your organization in the notebook's `configure(...)` cell:
  `ea.plugins.sliderule.configure(url="slideruleearth.io", organization="<your-org>")`.
- **Private forks.** These URLs assume the public `betolink` repos. A private
  copy needs a token wired into git auth.
- **Don't** run bare `uv run jupyter lab` from the earthaccess checkout — `uv run`
  may re-sync the environment and drop the notebook deps. Activate the venv and
  call `jupyter lab` (or use `uv run --no-sync jupyter lab`).
