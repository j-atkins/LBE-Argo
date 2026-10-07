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

**Open the app (on Molab) [here](https://molab.marimo.io/notebooks/nb_tUUNWQGyGS7MaUY2fsLJ7y/app)**

This is the finished notebook as an interactive app, with the code hidden. It may take a minute or two to start. Scroll down, and change the settings in the **Control room** to watch the plots update. Nothing to install.

Please note, as of October 2026 the app is running as expected. In case the link stops working, please [raise an Issue](https://github.com/j-atkins/LBE-Argo/issues) in this repository, and/or follow the instructions below to run the notebook in your own environment.

#### If the app link doesn't work, or you want to see and edit the code

[![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/j-atkins/LBE-Argo/blob/main/src/lbe_argo/analysis/argo_lbe_analysis.py)

This opens the notebook in [molab](https://molab.marimo.io/), marimo's free cloud notebooks. There is nothing to install, but you need to sign in to molab (a free account is enough). To get the finished, interactive version:

1. On the page that opens, click **"Run it now"** (the green link at the top) and sign in when asked.
2. A box asks "Run this notebook on a server?" and warns that the notebook "has not been verified by marimo". That warning appears for every notebook marimo hasn't reviewed. Click **"Run on server"**.
3. Wait for the server to start. The notebook doesn't run by itself here, so press the big yellow **play button** at the bottom-right of the page once. The first run takes a minute or two, while it installs what it needs and loads the data.
4. To hide the code and see just the results and explanations, click the **middle** one of the three buttons above the play button (the "app view" toggle). Click it again to get the code back.
5. Scroll down, and change the settings in the **Control room** to watch the plots update.

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

##### The shared app (for students)

Students are sent a single link to the notebook running as an app in [molab](https://molab.marimo.io/): the code is hidden, and there is no "Run on server" box, warning or play button. To set it up:

1. Open the notebook in molab with the badge at the top of this README, sign in, and click **"Save a copy"** to put a copy in your own workspace.
2. Press the play button, and wait for the notebook to finish running.
3. Click **Share**, choose **"Run as app"**, and copy the link. Replace `YOUR-APP-LINK` at the top of this README with it.

Things to keep in mind:

- **Updating it.** The saved copy is separate from this repository (molab says changes to the mirrored notebook "won't be saved"), so pushing to GitHub is not expected to change it. After a change, make a fresh copy from the new version and share that, or edit the copy in molab, and check what viewers of the old link see.
- **It shuts down when idle.** According to molab's documentation, notebooks idle for more than 90 minutes are shut down, and none run for longer than 12 hours. Whether a shared app link starts the notebook again for the next visitor isn't documented, so check the link from a signed-out browser the day before a class. If it has stopped, open your copy, press play and share it again.
- **Check it works signed out.** molab's documentation says people opening a shared app don't need an account, but test this, and test it with a few people at once before a whole class uses it.
- **Fall back to the steps above** if the app link isn't working on the day.

##### Static preview in molab (optional)

The badge link opens a read-only preview, which shows the notebook's code unless a session snapshot (the notebook's saved outputs) is stored next to it. To add one, run the notebook, then:

```bash
pixi run marimo export session src/lbe_argo/analysis/argo_lbe_analysis.py
git add -f src/lbe_argo/analysis/__marimo__/session/
```
