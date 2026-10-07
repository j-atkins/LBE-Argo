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

### ...or in your browser, with no setup

[![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/j-atkins/LBE-Argo/blob/main/src/lbe_argo/analysis/argo_lbe_analysis.py)

**For students:** on the page that opens, click **"Run it now"** (the green link at the top; no need to save or fork anything). Give it a minute or two to install and load the data the first time, then scroll down: the notebook runs itself, and you can change the settings in the **Control room** and watch the plots update. The code is hidden by default, so you only see the results and the explanations.

This opens the notebook in [molab](https://molab.marimo.io/), marimo's free cloud notebooks. The notebook's dependencies are listed in its header and installed automatically, and the (small) data it needs is downloaded from this repository, so there is nothing to set up. The simulation workflow below is not needed for this.

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
| `--years FIRST LAST` | Only generate expeditions for these years, e.g. `--years 1993 1995`. |
| `--seed N` | Random seed, to make the generated expeditions reproducible. |

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

| Option | Description |
| --- | --- |
| `--stream` | Stream ocean data with VirtualShip's normal methods instead of using local files. This skips the check that the needed dates are on disk, but simulations can be slower and may use more RAM. |
| `--workers N`, `-j N` | Number of simulations to run in parallel (default 4). Each run loads about a year of daily data, so check memory before upping this. |
| `--only NAME ...` | Run only the named expeditions, e.g. `--only 1993_H1 1993_H2`. |
| `--overwrite` | Rerun expeditions that already have results. The existing results are moved to `results_backup_<timestamp>/`. |

#### 4. Analyse the results

The analysis is a [marimo](https://marimo.io) notebook:

```bash
pixi run marimo edit src/lbe_argo/analysis/argo_lbe_analysis.py
```

The notebook reads slim copies of the simulation output (deployments, 6-hourly positions and profile samples; a few hundred kB per expedition instead of ~500 MB). They are built automatically on first use, or up front with:

```bash
pixi run python -m lbe_argo.processing.slim_results
```

All notebook settings live in its "control room": the deployment years and number of floats per year, and the eddy centre and radius. By default a float counts as inside the eddy when it is within 75 km of the LBE's observed centre (69.8°N, 3.5°E), or you can use a rough centre estimated from the ocean data on disk (the warmest water at 500 m in the Lofoten Basin).

#### 5. Share the notebook (optional)

The notebook only needs a few small files, which are bundled in [`data/bundled/`](data/bundled/) and committed to this repository: the slim simulation tables of every expedition (merged, ~25 MB) and the ocean background fields (bathymetry and the model's time-mean temperature at the 3D picture's depth slices, ~2.5 MB). This is what lets the notebook run anywhere, e.g. in [molab](https://molab.marimo.io/), without the simulation output or the hundreds of GB of raw ocean data (when the bundle isn't on disk, it is downloaded from GitHub). Rebuild it after changing the simulations or the map region, then commit the result:

```bash
pixi run python -m lbe_argo.processing.bundle_data
```

By default a notebook link opens as a static preview only if a session snapshot is stored next to the notebook. To add one (so visitors see the results before running anything), run the notebook, then:

```bash
pixi run marimo export session src/lbe_argo/analysis/argo_lbe_analysis.py
git add -f src/lbe_argo/analysis/__marimo__/session/
```
