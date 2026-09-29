# Virtual Argo floats & the Lofoten Basin Eddy

This PR houses the set-up, simulation and analysis of virtual Argo Float deployments in and around the Lofoton Basin Eddy, using [VirtualShip](https://github.com/Parcels-code/virtualship). This is intended as an educational resource, originally produced for a [U-Talent](https://u-talent.nl/) thesis project in 2026.

> [!NOTE]
> This project includes AI-generated (ClaudeCode) content. The author has reviewed and edited the content to ensure accuracy, relevance and clarity.

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

This writes an `expedition.yaml` to `data/expeditions/<YEAR>_H<1|2>/` for each half-year from 1993 to 2023. Each one contains randomly placed Argo float deployments in the upstream region along the Norwegian Atlantic Slope Current (66–68°N, 0–5°E).

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

The notebook locates the Lofoten Basin Eddy in the daily ocean data in `data/ocean/phys/` and caches the track to `data/ocean/lbe_track.parquet`. The cache is rebuilt whenever the set of daily files changes. To build it ahead of time, run:

```bash
pixi run python -m lbe_argo.analysis.eddy_tracking
```
