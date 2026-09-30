# Virtual Argo floats & the Lofoten Basin Eddy

This repository houses the set-up, simulation and analysis of virtual Argo Float deployments in and around the Lofoton Basin Eddy, using [VirtualShip](https://github.com/Parcels-code/virtualship). This is intended as an educational resource, originally produced for a [U-Talent](https://u-talent.nl/) thesis project in 2026.

> [!NOTE]
> This project includes AI-generated (ClaudeCode) content. The author has reviewed and edited the content to ensure (scientific) accuracy, relevance and clarity.

## To analyse the pre-computed results...

If you are here to explore the results of the simulations, you can skip the setup and simulation steps below. The analysis is a [marimo](https://marimo.io) notebook:

```bash
pixi run marimo edit src/lbe_argo/analysis/argo_lbe_analysis.py
```

> [!TIP]
> Install [pixi](https://pixi.prefix.dev/latest/) to run the notebook in a local environment and/or inteact with the simulation workflow [below](#more-technical-detail).

> [!IMPORTANT]
> Work in progress to host this notebook (with data) to be run in the browser without any local setup.

## More technical detail...

For those interested in reproducing/modifying the whole workflow, rather than just analysing the pre-computed results, see below.

### Setup

First, clone this repository:

```bash
git clone <repository-url>
```

Dependencies are managed with [pixi](https://pixi.sh):

```bash
pixi install
```

Run the commands below from the project root with `pixi run`, or open a shell in the environment with `pixi shell`.

Ocean data comes from the [Copernicus Marine Service](https://marine.copernicus.eu/). To download or stream it you need a Copernicus Marine account. Log in once with:

```bash
pixi run copernicusmarine login
```

### Workflow

All data is written under `data/`. The paths are set in [`src/lbe_argo/config.py`](src/lbe_argo/config.py), along with the Argo float settings (`ARGO_CONFIG`).

#### 1. Generate expeditions

```bash
pixi run python -m lbe_argo.processing.make_expeditions
```

This writes an `expedition.yaml` to `data/expeditions/<YEAR>_H<1|2>/` for each half-year from 1993 to 2023. Each one contains 1–2 Argo float releases per month, at random times and at random positions in the upstream region along the Norwegian Atlantic Slope Current (66–68°N, 0–5°E). Expeditions that already exist are left alone unless you pass `--overwrite`.

| Option | Description |
| --- | --- |
| `--strategy eddy` | Release the floats directly at the Lofoten Basin Eddy (within 20 km of its observed centre, 69.8°N, 3.5°E) instead of upstream. Expedition names get an `_eddy` suffix, e.g. `1993_H1_eddy`. |
| `--park-depth M` | Park (drift) the floats at `M` metres instead of the standard 1000 m. Expedition names get a `_park<M>m` suffix, e.g. `1993_H1_park800m`. |
| `--years FIRST LAST` | Only generate expeditions for these years, e.g. `--years 1993 1995`. |
| `--seed N` | Random seed, to make the generated expeditions reproducible. |

Because each experiment gets its own names, you can run several side by side and compare them in the notebook. For example, to add floats released at the eddy and parked at 800 m for 1993–1995:

```bash
pixi run python -m lbe_argo.processing.make_expeditions --strategy eddy --park-depth 800 --years 1993 1995
```

> [!NOTE]
> These are idealised experiments, so we've allowed ourselves to pick the parking/drift depth quite casually, e.g. shallower so that floats sit in the eddy's core (roughly 300–1000 m deep). With real Argo floats this isn't so simple. Most Argo floats park at 1000 m by standard design, so their data are comparable across the global array, and a different parking depth is a choice that has to be made before deployment.

#### 2. Download ocean data (optional)

```bash
pixi run python -m lbe_argo.processing.predownload_data
```

This downloads the global bathymetry file and daily physical ocean data files to `data/ocean/`. To change the date range, edit `dates` in [`predownload_data.py`](src/lbe_argo/processing/predownload_data.py). Set `OVERWRITE_EXISTING` in the same file to choose whether files that are already on disk are downloaded again.

Skip this step if you run the simulations with `--stream` (see below).

> [!WARNING]
Pre-downloading the full data will take a lot of disk space (estimate > 200GB) and many hours to complete. Try running with --stream (see below) if you don't have enough space.

#### 3. Run the simulations

```bash
pixi run python -m lbe_argo.simulate.run_simulations
```

This runs [VirtualShip](https://github.com/Parcels-code/virtualship) once for each expedition, with several runs in parallel. Results go to `<expedition_dir>/results/argo_float.parquet`. Each expedition's log is written to `<expedition_dir>/run.log`.

By default the simulations use the pre-downloaded data (`virtualship run --from-data`). Expeditions that need dates outside the downloaded range are skipped.

Only one flavour of experiment is run at a time. By default it's the standard one (`1993_H1`, `1993_H2`, ...).

| Option | Description |
| --- | --- |
| `--flavour SUFFIX` | Run a different experiment flavour, given by its expedition name suffix, e.g. `--flavour _eddy_park800m` runs `1993_H1_eddy_park800m`, `1993_H2_eddy_park800m`, ... |
| `--stream` | Stream ocean data with VirtualShip's normal methods instead of using local files. This skips the check that the needed dates are on disk, but simulations can be slower and may use more RAM. |
| `--workers N`, `-j N` | Number of simulations to run in parallel (default 4). Each run loads about a year of daily data, so check memory before upping this. |
| `--only NAME ...` | Run only the named expeditions, of any flavour, e.g. `--only 1993_H1 1993_H2_eddy`. Overrides `--flavour`. |
| `--overwrite` | Rerun expeditions that already have results. The existing results are moved to `results_backup_<timestamp>/`. |

#### 4. Analyse the results

The analysis is a [marimo](https://marimo.io) notebook:

```bash
pixi run marimo edit src/lbe_argo/analysis/argo_lbe_analysis.py
```

By default a float counts as inside the eddy when it is within 75 km of the LBE's observed centre (69.8°N, 3.5°E). The notebook lets you change the centre and radius, or use a rough centre estimated from the ocean data on disk (the warmest water at 500 m in the Lofoten Basin). It shows one experiment flavour at a time (e.g. standard, or `_eddy_park800m`), picked from a dropdown.
