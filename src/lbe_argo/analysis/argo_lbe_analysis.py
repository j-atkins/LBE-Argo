# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cartopy",
#     "cmocean",
#     "lbe-argo @ git+https://github.com/j-atkins/LBE-Argo.git",
#     "marimo",
#     "matplotlib",
#     "netcdf4",
#     "numpy",
#     "plotly",
#     "polars",
#     "pyarrow",
#     "pyyaml",
#     "scipy",
#     "xarray",
# ]
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(
    width="medium",
    app_title="Argo floats & the Lofoten Basin Eddy",
)


@app.cell
def _():
    import math
    import tempfile
    from pathlib import Path

    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import cmocean
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import polars as pl
    import xarray as xr
    from cartopy.geodesic import Geodesic
    from matplotlib.animation import FuncAnimation, HTMLWriter
    from matplotlib.collections import LineCollection
    from matplotlib.colors import ListedColormap
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    from lbe_argo.config import LBE_CENTRE
    from lbe_argo.processing.ocean_background import (
        MAP_EXTENT,
        load_bathymetry,
        load_model_mean_temp,
        model_data_available,
    )
    from lbe_argo.processing.slim_results import list_available, load_slim

    return (
        FuncAnimation,
        Geodesic,
        HTMLWriter,
        LBE_CENTRE,
        Line2D,
        LineCollection,
        ListedColormap,
        MAP_EXTENT,
        Patch,
        Path,
        ccrs,
        cfeature,
        cmocean,
        list_available,
        load_bathymetry,
        load_model_mean_temp,
        load_slim,
        math,
        mo,
        model_data_available,
        np,
        pl,
        plt,
        tempfile,
        xr,
    )


@app.cell
def _(mo):
    # next to the notebook if we have the repo, otherwise from GitHub (e.g. in the cloud)
    _notebook_dir = mo.notebook_dir()
    _logo = (
        _notebook_dir / "assets" / "virtual_ship_logo.png" if _notebook_dir else None
    )
    mo.image(
        _logo
        if _logo is not None and _logo.exists()
        else "https://raw.githubusercontent.com/j-atkins/LBE-Argo/main/src/lbe_argo/analysis/assets/virtual_ship_logo.png",
        width=500,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    def info_box(label, title, body, colour):
        """A textbook-style 'key facts' box: coloured edge, tinted background, small label."""
        return (
            f'<div style="border-left: 6px solid {colour}; border-radius: 6px; '
            f'padding: 0.9rem 1.2rem; background: rgba(128, 128, 128, 0.10);">'
            f'<div style="font: 700 11px sans-serif; letter-spacing: 0.14em; '
            f'color: {colour};">{label}</div>'
            f'<h3 style="margin: 0.4rem 0;">{title}</h3>'
            f"{mo.md(body).text}</div>"
        )

    _boxes = [
        info_box(
            "",
            "<b>The Lofoten Basin Eddy (LBE)</b>",
            'A long-lived eddy in the Lofoten Basin of the Norwegian Sea, centred near 70°N, 3.5°E. It stores a lot of warm, salty Atlantic Water at depth. The LBE is very interesting to study as a "natural laboratory" for understanding the influence of eddies on the properties of the surrounding ocean.',
            "#6186D5",
        ),
        info_box(
            "",
            "<b>Argo floats</b>",
            "A vital part of the modern-day ocean observation network, and one of the only systems for measuring subsurface ocean heat content around the world. Observations of our ocean are crucial for understanding and monitoring climate change, protecting ecosystems and providing data to feed into operational weather forecasting systems to improve predictions.",
            "#6186D5",
        ),
    ]

    mo.vstack(
        [
            mo.md("# Virtual Argo floats & the Lofoten Basin Eddy"),
            # a CSS grid makes both boxes the same height, however long their text is
            mo.Html(
                '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; '
                'align-items: stretch;">' + "".join(_boxes) + "</div>"
            ),
            mo.md(
                r"""
    ---

    This notebook centres around a "what if" scenario...

    As mentioned above, Argo floats are crucial for global observations but their coverage of the ocean is quite sparse and their deployment frequency can be tied to things like funding, which controls how many of them can even be deployed in a given year. Here, we are conducting our science in a hypothetical scenario: _what if_ we had a sustained Argo deployment programme in the North Atlantic / Nordic Seas, releasing a float or two every month in the area, year after year for approximately 30 years?

    - Would we get enough data to better understand the LBE and its influence on the surrounding ocean? More so than we do already?
    - What kind of physical features of the LBE would we be able to observe well? Temperature and salinity profiles, for example.
    - Do many of the deployments make it into the eddy? Remember we can't control Argo floats once they're released, they just drift with the ocean currents.
    - How many Argo floats do we need to deploy to get a good picture of what we're looking for?

    In addition to our results offering scientific insights into the characteristics of eddies, this exercise mimics the kind of task that oceanographers undertake when they are designing real-life observational campaigns. More floats means more cost, so it's really helpful to have an idea of what the data might look like, and what needs to be deployed when, before you spend millions of Euros on a real campaign. In other words, this is a very 'idealised' experiment. We are making a lot of 'ideal' world assumptions and conditions.
    """
            ),
        ]
    )
    return


@app.cell
def _(mo):
    callout_text = mo.md(r"""

    **Note**: It's always good to keep in mind that the Argo floats we're looking at in this notebook are *virtual*. They are simulated using the [VirtualShip](https://virtualship.parcels-code.org/) software, which carries each float through the currents of an ocean model (a 'digital twin of the ocean', more details  on that later...) and samples the model's temperature and salinity as the float profiles. Like a real Argo float, each one drifts at a depth of 1000m for 9 days, sinks to 2000m, then rises to the surface whilst measuring, and repeats this every 10 days.

    """)

    mo.callout(callout_text, kind="info")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## How 'idealised' is this?

    The experiment design is very idealised, which is on purpose. It's good to keep the following simplifications in mind when reading the results:


    - *The floats are released near the eddy, not in it.* Releases are at random positions
    in the Norwegian Atlantic Slope Current (66–68°N, 0–5°E), upstream of the Lofoten
    Basin. No sustained Argo campaign would put all its floats in one spot. Think of this
    as part of a wider North Atlantic campaign, in which we *hope* that a decent number
    of the floats get swept into the eddy (many won't though!).

    - *The region is small.* The ocean data in our domain only covers 64–78°N, 5°W–20°E (see the maps
    below). In our simulations, a float that leaves this box simply disappears from the simulation. For this reason, each float is given a lifetime of only about a year. Real Argo floats keep working for several years.

    - _The ocean here is a **model**._ The currents, temperature and salinity come from a modern ocean climate model (see [here](https://science.nasa.gov/kids/earth/what-are-climate-models/) for more information on what a climate model actually is).
        - Whilst generally very good at replicating real-life, models contain their own simplifications and assumptions. Relevant to our work here is that they often struggle to capture the _fine_ (small-scale) detail of the real life ocean. For example, fronts, small filaments and other small eddies which you may have read feed the larger LBE. Thankfully, the model we use here can capture the _large-scale_ features of the LBE (which you'll see later in this notebook) so it's still useful to us in this exercise. Regardless, it's best to consider our analysis here a *best-estimate representation* of the real eddy's behaviour, and the virtual Argo floats will only be able to capture the detail that the models can show.

    - *Real observations are not rich.* Even with hundreds of floats over many years, only a small fraction of profiles land in the eddy, at irregular times and places. Learning to work with that sparseness is a learning outcome in its own right, on top of what the data tell us about eddy properties.
    """)
    return


@app.cell
def _(mo):
    callout_text_ctrl_room = mo.md(r"""
    **Tip**: The "control room" below will let you thin out the campaign (reduce the number of Argo floats available etc.) and see how quickly the picture gets worse. This will be helpful when we start considering the implications of the results later in the notebook.
    """)

    mo.callout(callout_text_ctrl_room, kind="success")
    return


@app.cell
def _():
    ## PARAMS

    TRACK_COLOR = "#1c5cab"
    INSIDE_COLOR = "#eb6834"  # warm-core eddy -> orange
    OUTSIDE_COLOR = "#2a78d6"
    INK = "#0b0b0b"
    INK_MUTED = "#52514e"
    TRACK_ALPHA = 0.5

    NEW_PROFILE_GAP_S = 3600  # gap in ascent samples that starts a new profile
    R_EARTH_KM = 6371.0
    KM_PER_DEG = 111.19
    # upstream deployment corridor, see lbe_argo/processing/make_expeditions.py
    DEPLOY_BOX = dict(lat_min=66.0, lat_max=68.0, lon_min=0.0, lon_max=5.0)
    # default "inside eddy" radius around the LBE centre: wide, to cover its wandering
    EDDY_RADIUS_DEFAULT_KM = 75
    # where to look for the eddy's warm core in the model data (the Lofoten Basin)
    EDDY_SEARCH_BOX = dict(lat_min=68.5, lat_max=71.5, lon_min=0.0, lon_max=8.0)

    DENSITY_SEED = 42  # which floats are dropped when thinning the campaign

    # 3D composite: window around the eddy centre and grid spacing (depth slices: see
    # lbe_argo.processing.ocean_background)
    COMPOSITE_LEVEL_BIN_M = 30  # samples within this of a slice count towards it
    COMPOSITE_HALF_WIDTH_KM = 150
    COMPOSITE_GRID_KM = 6
    # Gaussian length scale for the Argo composite. NOTE: 25km is somewhat arbitrary and
    # only chosen for demonstration purposes; a real analysis would tune it to the data
    COMPOSITE_LENGTH_KM = 25
    CORE_RADIUS_KM = 30  # "near the core": within this of the model's eddy core

    ANIMATION_MAX_FRAMES = 180
    ANIMATION_MIN_STEP_DAYS = 5
    ANIMATION_TAIL_DAYS = 90
    return (
        ANIMATION_MAX_FRAMES,
        ANIMATION_MIN_STEP_DAYS,
        ANIMATION_TAIL_DAYS,
        COMPOSITE_GRID_KM,
        COMPOSITE_HALF_WIDTH_KM,
        COMPOSITE_LENGTH_KM,
        COMPOSITE_LEVEL_BIN_M,
        CORE_RADIUS_KM,
        DENSITY_SEED,
        DEPLOY_BOX,
        EDDY_RADIUS_DEFAULT_KM,
        EDDY_SEARCH_BOX,
        INK,
        INK_MUTED,
        INSIDE_COLOR,
        KM_PER_DEG,
        NEW_PROFILE_GAP_S,
        OUTSIDE_COLOR,
        R_EARTH_KM,
        TRACK_ALPHA,
        TRACK_COLOR,
    )


@app.cell
def _(list_available):
    # every expedition (e.g. 1993_H1) with simulation output, and how many floats it releases
    available = list_available()
    return (available,)


@app.cell(hide_code=True)
def _(available, mo):
    mo.stop(
        available.is_empty(),
        mo.callout(mo.md("No simulation results found yet."), kind="warn"),
    )
    mo.md(r"""

    ## The simulations

    Now let's get started with actually looking at the results of the virtual Argo float campaign.

    ### Experiment set up

    - **Floats**: 1000m drifting/parking depth, 2000m maximum depth, 10-day cycle period, 9-day drift at parking depth.
    - **Releases**: random positions in the Norwegian Atlantic Slope Current (66–68°N, 0–5°E), upstream of the Lofoten Basin, at a rate of up to 2 floats per month, for the selected years (default is 1993-2023).
    - **VirtualShip**: the software carries the floats by the currents of a modern ocean model and samples the model's temperature and salinity as they profile.

    ### Control room

    You can use this 'control room' to set certain parameters, which will influence the results you see. All of the plots later in the notebook will respond to changes you make here.

    - **Deployment years** and **floats deployed per year**: the size of the campaign. The
      simulations release up to about two floats per month; turn this down to mimic a
      tighter budget (fewer floats each year) and watch the picture get sparser in some of the plots later on in this notebook.
    - **Eddy**: where the eddy is, and how close to its centre counts as "inside". The
      default is the eddy's observed, quasi-permanent centre with a fairly wide radius (~ 75km),
      because the real eddy wanders a few tens of km. Alternatively, use the warmest
      water at 500m in the model's Lofoten Basin as the centre.
    - **Display**: the background of the map. The choices are bathymetry (otherwise known as ocean depth) or model temperature.
    """)
    return


@app.cell
def _(
    EDDY_RADIUS_DEFAULT_KM,
    LBE_CENTRE,
    available,
    mo,
    model_data_available,
    pl,
):
    _years = available["year"]
    year_range = mo.ui.range_slider(
        start=_years.min(),
        stop=_years.max(),
        step=1,
        value=[_years.min(), _years.max()],
        label="Deployment years",
        show_value=False,  # the built-in readout adds a thousands separator (1,993)
    )
    _max_per_year = (
        available.group_by("year").agg(pl.col("n_floats").sum())["n_floats"].max()
    )
    floats_per_year = mo.ui.slider(
        start=1,
        stop=_max_per_year,
        step=1,
        value=_max_per_year,
        label="Floats deployed per year",
        show_value=True,
    )
    centre_mode = mo.ui.dropdown(
        options=["Fixed", "Estimated from model data"]
        if model_data_available()
        else ["Fixed"],
        value="Fixed",
        label="Eddy centre",
    )
    centre_lat = mo.ui.number(
        start=66, stop=73, step=0.05, value=LBE_CENTRE["lat"], label="Fixed lat (°N)"
    )
    centre_lon = mo.ui.number(
        start=-4, stop=12, step=0.05, value=LBE_CENTRE["lon"], label="Fixed lon (°E)"
    )
    eddy_radius = mo.ui.slider(
        start=10,
        stop=200,
        step=5,
        value=EDDY_RADIUS_DEFAULT_KM,
        label="'Inside eddy' radius (km)",
        show_value=True,
    )
    map_background = mo.ui.dropdown(
        options=["Bathymetry", "Model mean temperature @ 500m"],
        value="Bathymetry",
        label="Map background",
    )
    return (
        centre_lat,
        centre_lon,
        centre_mode,
        eddy_radius,
        floats_per_year,
        map_background,
        year_range,
    )


@app.cell(hide_code=True)
def _(
    centre_lat,
    centre_lon,
    centre_mode,
    eddy_radius,
    floats_per_year,
    map_background,
    mo,
    year_range,
):
    _section = "margin: 0 0 4px; font: 600 11px monospace; letter-spacing: 0.12em; opacity: 0.65;"
    mo.vstack(
        [
            mo.Html(
                '<div style="font: 700 15px monospace; letter-spacing: 0.2em;">'
                '<span style="color: #2ea043;">●</span>&nbsp; CONTROL ROOM</div>'
            ),
            mo.Html(f'<div style="{_section}">CAMPAIGN</div>'),
            mo.hstack(
                [
                    mo.hstack(
                        [
                            year_range,
                            mo.md(f"**{year_range.value[0]}–{year_range.value[1]}**"),
                        ],
                        justify="start",
                        align="center",
                        gap=0.5,
                    ),
                    floats_per_year,
                ],
                justify="start",
                gap=2,
            ),
            mo.Html(f'<div style="{_section}">EDDY</div>'),
            mo.hstack(
                [centre_mode, centre_lat, centre_lon, eddy_radius],
                justify="start",
                gap=2,
            ),
            mo.Html(f'<div style="{_section}">DISPLAY</div>'),
            mo.hstack([map_background], justify="start", gap=2),
        ],
        gap=0.75,
    ).style(
        {
            "border": "2px solid #52514e",
            "border-radius": "10px",
            "padding": "1rem 1.25rem",
            "background": "rgba(128, 128, 128, 0.10)",
            "box-shadow": "0 4px 14px rgba(0, 0, 0, 0.25), inset 0 0 0 1px rgba(255, 255, 255, 0.15)",
        }
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Load simulation output
    """)
    return


@app.cell
def _(NEW_PROFILE_GAP_S, Path, available, load_slim, mo, pl, year_range):
    _todo = available.filter(pl.col("year").is_between(*year_range.value))

    _deployments, _tracks, _samples, skipped = [], [], [], []
    for _row in mo.status.progress_bar(
        _todo.rows(named=True),
        title="Loading float simulations",
        remove_on_exit=True,
    ):
        try:
            _tables = load_slim(Path(_row["expedition_dir"]))
        except (
            Exception
        ) as _err:  # e.g. parquet footer missing while a run is in progress
            skipped.append(f"{_row['expedition']} ({type(_err).__name__})")
            continue
        _float_id = (
            pl.lit(f"{_row['expedition']}_")
            + pl.col("particle_id").cast(pl.String).str.zfill(2)
        ).alias("float_id")
        _deployments.append(
            _tables["deployments"].with_columns(
                _float_id, expedition=pl.lit(_row["expedition"])
            )
        )
        _tracks.append(_tables["tracks"].with_columns(_float_id))
        _samples.append(_tables["samples"].with_columns(_float_id))

    mo.stop(
        not _deployments,
        mo.callout(
            mo.md(f"No readable results. Skipped: {', '.join(skipped) or 'none'}"),
            kind="warn",
        ),
    )

    deployments_loaded = pl.concat(_deployments).with_columns(
        deploy_year=pl.col("deploy_time").dt.year()
    )
    _deploy_info = deployments_loaded.select("float_id", "deploy_time", "deploy_year")
    _days_since = (
        (pl.col("time") - pl.col("deploy_time")).dt.total_seconds() / 86400
    ).alias("days_since_deploy")

    tracks_loaded = (
        pl.concat(_tracks)
        .join(_deploy_info, on="float_id")
        .with_columns(_days_since)
        .sort("float_id", "time")
    )
    samples_loaded = (
        pl.concat(_samples)
        .join(_deploy_info, on="float_id")
        .with_columns(_days_since, depth=-pl.col("z"))
        .sort("float_id", "time")
        .with_columns(
            profile_num=(pl.col("time").diff().dt.total_seconds() > NEW_PROFILE_GAP_S)
            .fill_null(False)
            .cum_sum()
            .over("float_id")
        )
        .with_columns(
            profile_id=pl.col("float_id") + "_p" + pl.col("profile_num").cast(pl.String)
        )
    )
    return deployments_loaded, samples_loaded, skipped, tracks_loaded


@app.cell
def _(EDDY_SEARCH_BOX, load_bathymetry, load_model_mean_temp, mo):
    # background fields: bathymetry, and the model's time-mean temperature at the 3D
    # picture's depth slices. Independent of the controls, so this only runs once.
    bathymetry = load_bathymetry()  # NaN on land

    with mo.status.spinner(title="Loading model temperature"):
        model_mean_temp = load_model_mean_temp()
    mean_temp_500m, model_eddy_centre = None, None
    if model_mean_temp is not None:
        mean_temp_500m = model_mean_temp.sel(depth=500)

        # rough eddy centre: the warmest (lightly smoothed) 500m water in the Lofoten Basin
        _box = EDDY_SEARCH_BOX
        _basin = (
            mean_temp_500m.sel(
                latitude=slice(_box["lat_min"], _box["lat_max"]),
                longitude=slice(_box["lon_min"], _box["lon_max"]),
            )
            .rolling(latitude=3, longitude=3, center=True, min_periods=1)
            .mean()
        )
        _warmest = _basin.where(_basin == _basin.max(), drop=True)
        model_eddy_centre = dict(
            lat=float(_warmest.latitude[0]), lon=float(_warmest.longitude[0])
        )
    return bathymetry, mean_temp_500m, model_eddy_centre, model_mean_temp


@app.cell
def _(
    DENSITY_SEED,
    R_EARTH_KM,
    centre_lat,
    centre_lon,
    centre_mode,
    deployments_loaded,
    eddy_radius,
    floats_per_year,
    math,
    model_eddy_centre,
    pl,
    samples_loaded,
    tracks_loaded,
):
    def distance_km(lat_col, lon_col, lat0, lon0):
        """Great-circle (haversine) distance from (lat0, lon0) as a polars expression."""
        phi, lam = pl.col(lat_col).radians(), pl.col(lon_col).radians()
        phi0, lam0 = math.radians(lat0), math.radians(lon0)
        a = ((phi - phi0) / 2).sin() ** 2 + phi.cos() * math.cos(phi0) * (
            (lam - lam0) / 2
        ).sin() ** 2
        return 2 * R_EARTH_KM * a.sqrt().arcsin()

    # eddy centre: fixed (observed LBE position by default) or estimated from the model data
    _centre = (
        model_eddy_centre
        if centre_mode.value.startswith("Estimated") and model_eddy_centre
        else dict(lat=centre_lat.value, lon=centre_lon.value)
    )
    eddy_summary = dict(
        lat=_centre["lat"], lon=_centre["lon"], radius_km=eddy_radius.value
    )
    radius_label = f"{eddy_radius.value}km"

    def with_eddy(df):
        """Add the distance to the eddy centre and whether that's inside the eddy radius."""
        return df.with_columns(
            dist_km=distance_km("y", "x", _centre["lat"], _centre["lon"])
        ).with_columns(inside=pl.col("dist_km") <= eddy_radius.value)

    # thin the campaign: keep the first N floats of each year in a fixed random order, so turning the density up only ever adds floats
    deployments = (
        deployments_loaded.with_columns(
            _rank=pl.col("float_id")
            .hash(seed=DENSITY_SEED)
            .rank("ordinal")
            .over("deploy_year")
        )
        .filter(pl.col("_rank") <= floats_per_year.value)
        .drop("_rank")
    )
    _keep = pl.col("float_id").is_in(deployments["float_id"].implode())

    tracks = with_eddy(tracks_loaded.filter(_keep))
    _samples = samples_loaded.filter(_keep)

    # one row per profile, located at the mean position of its ascent
    profiles = with_eddy(
        _samples.group_by("profile_id", maintain_order=True).agg(
            pl.col("float_id", "deploy_year").first(),
            pl.col("time").last(),
            pl.col("days_since_deploy").last(),
            pl.col("x", "y").mean(),
        )
    )
    samples = _samples.join(
        profiles.select("profile_id", "inside", "dist_km"), on="profile_id"
    )
    return deployments, eddy_summary, profiles, radius_label, samples, tracks


@app.cell(hide_code=True)
def _(deployments, mo, model_eddy_centre, profiles, skipped):
    _n_inside = int(profiles["inside"].sum())
    _msg = (
        f"There are **{deployments.height:,}** Argo floats deployed over "
        f"**{deployments['deploy_year'].n_unique()}** year(s). "
        f"This gives a total of **{profiles.height:,}** vertical sampling profiles, of which **{_n_inside:,}** "
        f"({100 * _n_inside / max(profiles.height, 1):.0f}%) are taken inside the eddy."
    )
    if model_eddy_centre:
        _msg += (
            f"\n\nThe model-estimated eddy centre (warmest 500m water in the basin) is at: "
            f"{model_eddy_centre['lat']:.2f}°N, {model_eddy_centre['lon']:.2f}°E."
        )
    if skipped:
        _msg += f"\n\nSkipped (unreadable/incomplete): {', '.join(skipped)}"
    mo.callout(mo.md(_msg), kind="warn" if skipped else "info")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1) Where do the floats go?

    The map below shows every float track at 6-hourly positions across the lifetime (blue lines). Black open circles mark the release locations (the dashed box is the deployment corridor). The wider, dashed orange circle is the "inside eddy" region and the small, orange circles mark where each Argo float vertical profile within the eddy was taken.

    Note that some floats simply end at the edge of the map! That's where the model domain stops.
    """)
    return


@app.cell
def _(
    DEPLOY_BOX,
    Geodesic,
    INK,
    INK_MUTED,
    INSIDE_COLOR,
    Line2D,
    LineCollection,
    ListedColormap,
    MAP_EXTENT,
    Patch,
    TRACK_ALPHA,
    TRACK_COLOR,
    bathymetry,
    ccrs,
    cfeature,
    cmocean,
    deployments,
    eddy_summary,
    map_background,
    mean_temp_500m,
    np,
    pl,
    plt,
    profiles,
    radius_label,
    tracks,
):
    def pale(cmap, strength):
        """Opaque, washed-out copy of a colormap (translucent cells leave seams once reprojected)."""
        rgb = cmap(np.linspace(0, 1, 256))[:, :3]
        return ListedColormap(strength * rgb + (1 - strength))

    def draw_basemap(ax, background="Bathymetry", colorbar_fig=None):
        """Background field, depth contours, land, deployment box and eddy circle."""
        pc = ccrs.PlateCarree()
        ax.set_extent(MAP_EXTENT, crs=pc)
        mesh_kw = dict(transform=pc, zorder=0, shading="auto", rasterized=True)
        if background == "Bathymetry" or mean_temp_500m is None:
            mesh = ax.pcolormesh(
                bathymetry.longitude,
                bathymetry.latitude,
                bathymetry,
                cmap=pale(cmocean.cm.deep, 0.55),
                vmin=0,
                vmax=5000,
                **mesh_kw,
            )
            cbar_label = "Depth (m)"
        else:
            mesh = ax.pcolormesh(
                mean_temp_500m.longitude,
                mean_temp_500m.latitude,
                mean_temp_500m,
                cmap=pale(cmocean.cm.thermal, 0.55),
                **mesh_kw,
            )
            cbar_label = "Model mean temperature @ 500m (°C)"
        ax.contour(
            bathymetry.longitude,
            bathymetry.latitude,
            bathymetry,
            levels=[1000, 2000, 3000],
            colors=INK_MUTED,
            linewidths=0.4,
            alpha=0.6,
            transform=pc,
        )
        ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="tan", zorder=1)
        ax.coastlines(resolution="50m", linewidth=0.6, color=INK_MUTED, zorder=2)
        if colorbar_fig is not None:
            colorbar_fig.colorbar(mesh, ax=ax, shrink=0.6, pad=0.02, label=cbar_label)

        box = DEPLOY_BOX
        ax.plot(
            [
                box["lon_min"],
                box["lon_max"],
                box["lon_max"],
                box["lon_min"],
                box["lon_min"],
            ],
            [
                box["lat_min"],
                box["lat_min"],
                box["lat_max"],
                box["lat_max"],
                box["lat_min"],
            ],
            color=INK,
            linestyle="--",
            linewidth=1.0,
            transform=pc,
            zorder=4,
        )
        elon, elat = eddy_summary["lon"], eddy_summary["lat"]
        circle = Geodesic().circle(
            elon, elat, eddy_summary["radius_km"] * 1e3, n_samples=120
        )
        ax.fill(
            circle[:, 0],
            circle[:, 1],
            color=INSIDE_COLOR,
            alpha=0.15,
            transform=pc,
            zorder=5,
        )
        ax.plot(
            circle[:, 0],
            circle[:, 1],
            color=INSIDE_COLOR,
            linewidth=2,
            linestyle="--",
            transform=pc,
            zorder=5,
        )
        ax.plot(
            elon,
            elat,
            marker="+",
            color=INSIDE_COLOR,
            markersize=10,
            mew=2,
            transform=pc,
            zorder=5,
        )

    MAP_PROJ = ccrs.NorthPolarStereo(central_longitude=7.5)
    _pc = ccrs.PlateCarree()
    fig_map, _ax = plt.subplots(figsize=(9, 8), subplot_kw=dict(projection=MAP_PROJ))
    draw_basemap(_ax, map_background.value, colorbar_fig=fig_map)

    # tracks, one LineCollection so thousands of floats stay fast
    _segments = [
        MAP_PROJ.transform_points(_pc, np.asarray(_xs), np.asarray(_ys))[:, :2]
        for _xs, _ys in tracks.group_by("float_id", maintain_order=True)
        .agg("x", "y")
        .select("x", "y")
        .iter_rows()
    ]
    _ax.add_collection(
        LineCollection(
            _segments, colors=TRACK_COLOR, alpha=TRACK_ALPHA, linewidths=0.5, zorder=3
        )
    )

    # profile locations: small open circles, only for profiles inside the eddy
    _inside = profiles.filter(pl.col("inside"))
    _ax.scatter(
        _inside["x"],
        _inside["y"],
        s=7,
        facecolors="none",
        linewidths=0.5,
        alpha=0.6,
        edgecolors=INSIDE_COLOR,
        transform=_pc,
        zorder=4,
    )
    _ax.scatter(
        deployments["lon0"],
        deployments["lat0"],
        s=9,
        facecolors="none",
        edgecolors=INK,
        linewidths=0.6,
        transform=_pc,
        zorder=6,
    )

    _gl = _ax.gridlines(draw_labels=True, linewidth=0.3, color=INK_MUTED, alpha=0.5)
    _gl.top_labels = _gl.right_labels = False

    _handles = [
        Line2D([], [], color=TRACK_COLOR, alpha=TRACK_ALPHA, lw=2, label="Float track"),
        Line2D(
            [],
            [],
            marker="o",
            mfc="none",
            mec=INK,
            lw=0,
            markersize=4,
            label="Argo float release",
        ),
        Line2D(
            [],
            [],
            marker="o",
            mfc="none",
            mec=INSIDE_COLOR,
            mew=0.8,
            lw=0,
            markersize=4,
            label="Vertical profile inside eddy",
        ),
        Patch(
            facecolor=INSIDE_COLOR,
            alpha=0.3,
            edgecolor=INSIDE_COLOR,
            label=f"LBE (r = {radius_label})",
        ),
    ]
    _ax.legend(handles=_handles, loc="upper left", fontsize=8, framealpha=0.9)
    _ax.set_title(
        "Virtual Argo float tracks & the Lofoten Basin Eddy", loc="left", fontsize=11
    )
    fig_map.tight_layout()
    fig_map
    return MAP_PROJ, draw_basemap


@app.cell(hide_code=True)
def _(ANIMATION_TAIL_DAYS, mo):
    mo.md(rf"""
    ### Watching the campaign unfold

    The animation below shows the same floats as the map above, but now through time. Each dot is a float that is still alive and in the domain, with a {ANIMATION_TAIL_DAYS}-day tail so that you can track it by eye easier. Floats vanish when they reach the end of their lifetime or drift out of the domain. Rendering takes a little while, so it only runs on request (press the button again after changing control-room settings).
    """)
    return


@app.cell
def _(mo):
    animate_button = mo.ui.run_button(label="Build animation")
    animate_button
    return (animate_button,)


@app.cell
def _(
    ANIMATION_MAX_FRAMES,
    ANIMATION_MIN_STEP_DAYS,
    ANIMATION_TAIL_DAYS,
    FuncAnimation,
    HTMLWriter,
    INK,
    INSIDE_COLOR,
    LineCollection,
    MAP_PROJ,
    OUTSIDE_COLOR,
    TRACK_COLOR,
    animate_button,
    ccrs,
    deployments,
    draw_basemap,
    mo,
    np,
    pl,
    plt,
    tempfile,
    tracks,
):
    mo.stop(not animate_button.value, mo.md("_Press **Build animation** to render._"))

    _t0 = tracks["time"].min()
    _span_days = (tracks["time"].max() - _t0).total_seconds() / 86400
    _step = max(ANIMATION_MIN_STEP_DAYS, _span_days / ANIMATION_MAX_FRAMES)
    _frames = np.arange(0, _span_days + _step, _step)

    _days = ((pl.col("time") - _t0).dt.total_seconds() / 86400).alias("t_days")
    _xy = MAP_PROJ.transform_points(
        ccrs.PlateCarree(), tracks["x"].to_numpy(), tracks["y"].to_numpy()
    )
    _tr = tracks.select("float_id", "inside", _days).with_columns(
        px=_xy[:, 0], py=_xy[:, 1]
    )
    _xy0 = MAP_PROJ.transform_points(
        ccrs.PlateCarree(),
        deployments["lon0"].to_numpy(),
        deployments["lat0"].to_numpy(),
    )
    _releases = deployments.select(
        ((pl.col("deploy_time") - _t0).dt.total_seconds() / 86400).alias("t_days")
    ).with_columns(px=_xy0[:, 0], py=_xy0[:, 1])

    _fig, _ax = plt.subplots(
        figsize=(5.5, 6), dpi=96, subplot_kw=dict(projection=MAP_PROJ)
    )
    _fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.94)
    draw_basemap(_ax)
    _tails = LineCollection([], colors=TRACK_COLOR, linewidths=0.8, alpha=0.5, zorder=6)
    _ax.add_collection(_tails)
    _heads = _ax.scatter([], [], s=14, zorder=7, edgecolors="white", linewidths=0.4)
    _new = _ax.scatter(
        [], [], s=60, facecolors="none", edgecolors=INK, linewidths=1.2, zorder=8
    )
    _label = _ax.set_title("", loc="left", fontsize=10)

    def _update(day):
        win = _tr.filter(pl.col("t_days").is_between(day - ANIMATION_TAIL_DAYS, day))
        per_float = win.group_by("float_id").agg("px", "py", pl.col("inside").last())
        _tails.set_segments(
            [
                np.column_stack([x, y])
                for x, y in per_float.select("px", "py").iter_rows()
            ]
        )
        heads = np.column_stack(
            [per_float["px"].list.last(), per_float["py"].list.last()]
        ).reshape(-1, 2)
        _heads.set_offsets(heads)
        _heads.set_color(
            [INSIDE_COLOR if i else OUTSIDE_COLOR for i in per_float["inside"]]
        )
        new = _releases.filter(pl.col("t_days").is_between(day - _step, day))
        _new.set_offsets(np.column_stack([new["px"], new["py"]]).reshape(-1, 2))
        date = _t0 + np.timedelta64(int(day * 86400), "s")
        _label.set_text(
            f"{date:%Y-%m-%d}  \u00b7  {per_float.height} active floats, "
            f"{int(per_float['inside'].sum())} inside the eddy"
        )
        return _tails, _heads, _new, _label

    with mo.status.spinner(title=f"Rendering {len(_frames)} frames"):
        _anim = FuncAnimation(_fig, _update, frames=_frames, interval=120)
        # Frames are rendered at 1.5x the displayed size (so they stay sharp on high-res
        # screens) and saved as high-quality jpegs, which keep the embedded animation to a
        # few tens of MB rather than hundreds
        with plt.rc_context({"animation.frame_format": "jpeg"}):
            with tempfile.TemporaryDirectory() as _tmp:
                _path = f"{_tmp}/animation.html"
                _anim.save(
                    _path,
                    writer=HTMLWriter(
                        fps=1000 / 120, embed_frames=True, default_mode="once"
                    ),
                    dpi=144,
                    savefig_kwargs=dict(pil_kwargs=dict(quality=92)),
                )
                _html = open(_path).read()
    plt.close(_fig)
    # show the (larger) frames at the original size; mo.Html doesn't run the player's
    # <script>, an iframe does
    _html += "<style>img { width: 528px; height: auto; }</style>"
    mo.iframe(_html, height="560px")
    return


@app.cell
def _(mo):
    callout_text_slow_animation = mo.md(r"""
    **Tip**: Use the `-` button to slow the animation down if you want to watch more carefully! Or the `+` to speed it back up.
    """)

    mo.callout(callout_text_slow_animation, kind="success")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2) Do the floats go into the eddy?

    In the animation above, you can see that many of the Argo floats don't make it into the eddy, but some do and if you look carefully you can see how some get caught up in its rotation. It could be that the eddy rotational exterior is a bit of a barrier to eddies entering so they have to be 'lucky' to get in (?) Or maybe at the standard-operational drifting depth of 1000m they are beneath the core of the eddy (tip: good to investigate how deep the eddy's influence extends!) and so don't get pulled in as easily?

    Below we'll also plot the proportion of Argo floats which make it into the eddy across the lifetime. You'll see that many of them actually take a long time (over 300 days) to make it into the eddy!
    """)
    return


@app.cell
def _(np, pl, plt, tracks):
    _daily = (
        tracks.with_columns(day=pl.col("days_since_deploy").floor())
        .group_by("day")
        .agg(
            frac_inside=pl.col("inside").mean(),
            n_floats=pl.col("float_id").n_unique(),
        )
        .filter(pl.col("n_floats") >= 3)
        .sort("day")
    )

    fig_gravity, _ax = plt.subplots(figsize=(10, 3.2))
    _ax.fill_between(
        _daily["day"],
        0,
        100 * _daily["frac_inside"],
        color="dodgerblue",
        alpha=0.5,
        lw=0,
        zorder=5,
    )
    _ax.plot(_daily["day"], 100 * _daily["frac_inside"], color="dodgerblue", lw=2.5)
    _ax.set_ylabel("Floats inside\neddy (%)")
    _ax.set_xlabel("Days since deployment")
    _ax.set_ylim(
        0, max(5, 100 * np.nanmax(_daily["frac_inside"].to_numpy(), initial=0) * 1.15)
    )
    _ax.set_facecolor("gainsboro")
    _ax.grid(color="white", linewidth=1)
    _ax.spines[["top", "right"]].set_visible(False)
    fig_gravity.tight_layout()
    fig_gravity
    return


@app.cell(hide_code=True)
def _(deployments, mo, pl, profiles, radius_label, tracks):
    _keys = ["deploy_year"]
    _by_year = (
        profiles.group_by(_keys)
        .agg(
            profiles=pl.len(),
            inside=pl.col("inside").sum(),
        )
        .join(
            tracks.group_by(_keys).agg(
                float_days_inside_pct=(pl.col("inside").mean() * 100).round(1),
                ever_inside=pl.col("float_id").filter(pl.col("inside")).n_unique(),
            ),
            on=_keys,
        )
        .join(deployments.group_by(_keys).agg(floats=pl.len()), on=_keys)
        .with_columns(inside_pct=(100 * pl.col("inside") / pl.col("profiles")).round(1))
        .sort(_keys)
        .select(
            pl.col("deploy_year").alias("Deployment year"),
            pl.col("floats").alias("Floats"),
            pl.col("ever_inside").alias("Floats ever inside eddy"),
            pl.col("float_days_inside_pct").alias("Float-time inside (%)"),
            pl.col("profiles").alias("Profiles"),
            pl.col("inside").alias("Profiles inside eddy"),
            pl.col("inside_pct").alias("Profiles inside (%)"),
        )
    )
    mo.vstack(
        [
            mo.md(f"**Summary by deployment year** (eddy radius {radius_label})"),
            mo.ui.table(
                _by_year,
                selection=None,
                format_mapping={"Deployment year": str},
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3) Profiles inside vs. outside the eddy

    Each time a float rises from 2000m to the surface it measures a **profile**: the
    temperature and salinity of the water at every depth on the way up. Below, every
    profile is a thin coloured line, split into those taken *inside* the eddy (left) and
    *outside* it (right). The thick black line is the median. This is the "average" or "typical" profile.
    """)
    return


@app.cell
def _(mo):
    callout_how_read = mo.md(r"""

    **TIP**: The plots may look a bit upside-down at first! Depth runs *down the y-axis*, with the surface (0m) at the top and 2000m at the bottom, just like looking down into the ocean. Temperature or salinity runs *along the x-axis*. So to read a line, start at the top and follow it downwards: moving left or right tells you how much colder/warmer (or fresher/saltier) the water gets as you go deeper. A line that stays far to the right all the way down is warm (or salty) water at depth.

    """)

    mo.callout(callout_how_read, kind="success")
    return


@app.cell
def _(pl):
    VARIABLES = {
        "temperature": "Temperature (°C)",
        "salinity": "Salinity (PSU)",
    }

    def binned_profile(df, var, bin_m=25, min_count=5):
        """Median and inter-quartile range of `var` in depth bins."""
        return (
            df.with_columns(
                depth_bin=(pl.col("depth") / bin_m).floor() * bin_m + bin_m / 2
            )
            .group_by("depth_bin")
            .agg(
                q25=pl.col(var).quantile(0.25),
                median=pl.col(var).median(),
                q75=pl.col(var).quantile(0.75),
                n=pl.len(),
            )
            .filter(pl.col("n") >= min_count)
            .sort("depth_bin")
        )

    return VARIABLES, binned_profile


@app.cell
def _(
    INK,
    INK_MUTED,
    INSIDE_COLOR,
    LineCollection,
    OUTSIDE_COLOR,
    VARIABLES,
    binned_profile,
    pl,
    plt,
    samples,
):
    _groups = {
        "Inside eddy": (samples.filter(pl.col("inside")), INSIDE_COLOR),
        "Outside eddy": (samples.filter(~pl.col("inside")), OUTSIDE_COLOR),
    }
    # depth axis shared across all panels, each variable's axis shared along its row
    fig_profiles, _axes = plt.subplots(
        len(VARIABLES), 2, figsize=(10, 7.5), squeeze=False, sharex="row", sharey=True
    )

    for _col, (_title, (_df, _color)) in enumerate(_groups.items()):
        _per_profile = _df.group_by("profile_id", maintain_order=True).agg(
            "depth", *VARIABLES
        )
        for _row, (_var, _label) in enumerate(VARIABLES.items()):
            _ax = _axes[_row, _col]
            _segments = [
                list(zip(v, d))
                for d, v in zip(_per_profile["depth"], _per_profile[_var])
            ]
            _ax.add_collection(
                LineCollection(_segments, colors=_color, alpha=0.3, linewidths=0.4)
            )
            if _df.height:
                _med = binned_profile(_df, _var)
                _ax.plot(_med["median"], _med["depth_bin"], color=INK, lw=2)
            else:
                _ax.text(
                    0.5,
                    0.5,
                    "No profiles",
                    transform=_ax.transAxes,
                    ha="center",
                    color=INK_MUTED,
                )
            _ax.autoscale_view()
            _ax.set_facecolor("gainsboro")
            _ax.grid(color="white", linewidth=0.75)
            _ax.spines[["top", "right"]].set_visible(False)
            _ax.set_xlabel(_label)
            if _col == 0:
                _ax.set_ylabel("Depth (m)")
        _axes[0, _col].set_title(
            f"{_title}  ·  {_per_profile.height:,} profiles", loc="left", fontsize=10
        )

    for _ax in _axes.flat:
        _ax.set_ylim(2000, 0)
    fig_profiles.tight_layout()
    fig_profiles
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Inside vs. outside comparison

    The plots above kept the inside and outside profiles separate, with every individual profile drawn as its own thin line. That shows how much the profiles vary, but it makes the two groups hard to compare directly. Here we combine each group down to a single "typical" profile and draw inside (orange) and outside (blue) on the same axes, so any differences stand out.

    The line is the median/average profile at each depth and the shaded band is the inter-quartile range, which is the spread of the middle half of the profiles at that depth (from the 25th to the 75th percentile). A wide band means the profiles disagree a lot and a narrow band means they are similar. The number in the legend (n) is how many profiles went into each group.

    Where the two lines are far apart, the water inside the eddy really does differ from the water outside it. Where the bands overlap a lot, the difference is small compared with the natural variability, so be more cautious about reading anything into it. Depth is still on the y-axis, with the surface at the top.
    """)
    return


@app.cell
def _(
    INSIDE_COLOR,
    OUTSIDE_COLOR,
    VARIABLES,
    binned_profile,
    pl,
    plt,
    samples,
):
    fig_compare, _axes = plt.subplots(
        1, len(VARIABLES), figsize=(10, 4.2), squeeze=False
    )
    for _ax, (_var, _label) in zip(_axes[0], VARIABLES.items()):
        for _name, _mask, _color in [
            ("Inside eddy", pl.col("inside"), INSIDE_COLOR),
            ("Outside eddy", ~pl.col("inside"), OUTSIDE_COLOR),
        ]:
            _stats = binned_profile(samples.filter(_mask), _var)
            if _stats.height == 0:
                continue
            _n = samples.filter(_mask)["profile_id"].n_unique()
            _ax.fill_betweenx(
                _stats["depth_bin"],
                _stats["q25"],
                _stats["q75"],
                color=_color,
                alpha=0.15,
                lw=0,
            )
            _ax.plot(
                _stats["median"],
                _stats["depth_bin"],
                color=_color,
                lw=2,
                label=f"{_name} (n={_n:,})",
            )
        _ax.set_ylim(2000, 0)
        _ax.set(xlabel=_label, ylabel="Depth (m)")
        _ax.set_facecolor("gainsboro")
        _ax.grid(color="white", linewidth=0.75)
        _ax.spines[["top", "right"]].set_visible(False)
        _ax.legend(fontsize=8)
    fig_compare.tight_layout()
    fig_compare
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### What do the profiles tell us?

    Now let's put our Oceanographer hats on and interpret the results. Compare the inside and outside lines in the
    plots above:

    - Is the water warmer inside or outside the eddy? Which is saltier? Is the difference the same at every depth, or does it change as you go down?
    - What might the properties of the water compared to the its surroundings tell us about where it came from?
    - How does the eddy develop and maintain different conditions? Think about its rotation...
    - Why does this matter? If warm, salty water reaches hundreds of metres down inside the eddy, what does that say about how much heat it stores, and why might that matter for the climate of the region?
    - How sure can you be? Is this a good number of profiles to have to tell us confidently?
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 4) Putting it together: a 3D picture of the eddy

    For a bit of fun... what if we pooled *every* Argo float profile taken near the eddy, over all the selected years,
    into one combined, three-dimensional picture? The plot below attempts to do that...

    In the plot, the ocean is shown as a stack of horizontal cross-sections/slices at different depths through the water columm, each covering 150km either side of the eddy centre. The colour is the temperature **anomaly**, which means how much warmer (red) or colder (blue) the water is than average in that location. A warm-core eddy shows up as a warm, red blob that reaches down through the slices.

    On the left ("ARGO COMPOSITE") is the picture that can be created when all of the observations from the Argo floats across the campaign are combined. On the right ("OCEAN MODEL") is the model "truth", or the field the Argo floats are sampling (the 'digital twin' subsitute for real life). In this case it can be considered the picture of what a *perfect* observing system would be able to see. So comparing the two is a useful way of seeing how close the Argo float campaign gets to observing what's really happening.

    The orange dashed circles are the "inside eddy" region and the black vertical line marks the eddy core in the model (its warmest 500m water).

    Notice that the Argo panel largely misses the peak temperatures in the core. That's because very few floats ever profile right inside it (see the
    table below), so picture in the centre has to be filled in from the many
    profiles *around* the eddy but not from the core itself. The few that do get close are also mixed from different
    years and seasons, while the eddy itself wanders around its mean position.

    This is the observing problem in a nutshell... it's near impossible to get a complete picture of real life at all locations at all times. So the aim becomes to do as best we can!

    Now head back to the **control room** and turn down *floats deployed per year* or the year range, and watch the Argo picture break up further while the model panel stays the same.
    """)
    return


@app.cell
def _(mo):
    callout_try_plot = mo.md(r"""

    **Try it out!** Use the slider under the picture to move up and down through the ocean. Choose "All depths" to see everything at once. You can also click and drag to rotate the picture (select "Orbital rotation in the top right"), scroll to zoom, and hover over a slice to read off the temperature anomaly.

    """)

    mo.callout(callout_try_plot, kind="success")
    return


@app.cell
def _(mo):
    callout_plot_notes = mo.md(r"""

    **NOTE**: There are a few details to keep in mind when interpreting this plot...

    - Read the colourbar! The eddy's effect on temperature fades with depth. It is roughly
    1 °C in its core, but only a few hundredths of a degree by 1600m. If every slice used
    the same colour scale, the deep ones would look completely blank. So each slice has its own colour scale, adjusted to the magnitude of values at each depth. Therefore, the numbers on the colourbar also change as you move the slider. This means you can compare the shape of the eddy from slice to slice, but to compare how strong it is you have
    to read the numbers on the colourbar, not just the colours.

    - To make the Argo float composite plot, we use the sampled data combined with some statistical methods to make it a continuous picture in space. Where there aren't enough profiles taken by an Argo float in the simulations, there will be a gap in the plot because there isn't enough data to determine a value over that area.

    """)

    mo.callout(callout_plot_notes, kind="info")
    return


@app.cell
def _(
    COMPOSITE_GRID_KM,
    COMPOSITE_HALF_WIDTH_KM,
    COMPOSITE_LENGTH_KM,
    COMPOSITE_LEVEL_BIN_M,
    KM_PER_DEG,
    eddy_summary,
    model_eddy_centre,
    model_mean_temp,
    np,
    pl,
    samples,
    xr,
):
    # common grid, in km east/north of the eddy centre
    _lat0, _lon0 = eddy_summary["lat"], eddy_summary["lon"]
    _km_per_deg_lon = KM_PER_DEG * np.cos(np.radians(_lat0))
    grid_km = np.arange(
        -COMPOSITE_HALF_WIDTH_KM, COMPOSITE_HALF_WIDTH_KM + 1e-6, COMPOSITE_GRID_KM
    )
    grid_x, grid_y = np.meshgrid(grid_km, grid_km)
    composite_depths = model_mean_temp.depth.values

    # model "truth" on the grid, and its mean over the window at each depth (the reference
    # for anomalies, used for the Argo composite too)
    _dims = ("gy", "gx")
    model_on_grid = model_mean_temp.interp(
        latitude=xr.DataArray(_lat0 + grid_y / KM_PER_DEG, dims=_dims),
        longitude=xr.DataArray(_lon0 + grid_x / _km_per_deg_lon, dims=_dims),
    )
    _level_mean = model_on_grid.mean(_dims).values
    model_anomaly = model_on_grid.values - _level_mean[:, None, None]

    def argo_composite(df):
        """Gaussian-weighted map of temperature anomaly at each depth, plus the profile positions used."""
        L = COMPOSITE_LENGTH_KM
        fields = np.full((len(composite_depths), *grid_x.shape), np.nan)
        points = []
        for i, depth in enumerate(composite_depths):
            per_profile = (
                df.filter((pl.col("depth") - depth).abs() <= COMPOSITE_LEVEL_BIN_M)
                .group_by("profile_id")
                .agg(pl.col("x", "y", "temperature").mean())
                .with_columns(
                    px=(pl.col("x") - _lon0) * _km_per_deg_lon,
                    py=(pl.col("y") - _lat0) * KM_PER_DEG,
                )
                .filter(
                    (pl.col("px").abs() <= COMPOSITE_HALF_WIDTH_KM + 2 * L)
                    & (pl.col("py").abs() <= COMPOSITE_HALF_WIDTH_KM + 2 * L)
                )
            )
            px, py = per_profile["px"].to_numpy(), per_profile["py"].to_numpy()
            anomaly = per_profile["temperature"].to_numpy() - _level_mean[i]
            points.append((px, py))
            if not len(px):
                continue
            d2 = (grid_x[..., None] - px) ** 2 + (grid_y[..., None] - py) ** 2
            w = np.exp(-d2 / (2 * L**2)).astype(np.float32)
            wsum = w.sum(-1)
            field = (w * anomaly).sum(-1) / np.where(wsum > 0, wsum, 1)
            # blank where the nearest profile is further than ~1.5 L away
            field[wsum < np.exp(-0.5 * 1.5**2)] = np.nan
            fields[i] = field
        return fields, points

    argo_fields, argo_points = argo_composite(samples)

    # the model's eddy core, in the same km coordinates
    model_core_km = (
        (model_eddy_centre["lon"] - _lon0) * _km_per_deg_lon,
        (model_eddy_centre["lat"] - _lat0) * KM_PER_DEG,
    )
    return (
        argo_fields,
        argo_points,
        composite_depths,
        grid_x,
        grid_y,
        model_anomaly,
        model_core_km,
    )


@app.cell
def _(
    COMPOSITE_HALF_WIDTH_KM,
    INSIDE_COLOR,
    TRACK_COLOR,
    argo_fields,
    cmocean,
    composite_depths,
    eddy_summary,
    grid_x,
    grid_y,
    model_anomaly,
    model_core_km,
    np,
):
    import plotly.graph_objects as go

    # Anomalies shrink with depth (~1 °C in the core, a few hundredths at 1600m). Each slice
    # is therefore scaled by the model's anomaly range at that depth (99th percentile), and
    # the colourbar is relabelled in real °C for whichever slice the slider has selected.
    _scale = np.nanpercentile(np.abs(model_anomaly), 99, axis=(1, 2))
    _n = len(composite_depths)
    _w = COMPOSITE_HALF_WIDTH_KM
    _theta = np.linspace(0, 2 * np.pi, 100)
    _MODEL_COLOR = "#2b8a6e"
    _colorscale = [
        [
            v,
            "rgb({:.0f},{:.0f},{:.0f})".format(
                *(255 * np.array(cmocean.cm.balance(v))[:3])
            ),
        ]
        for v in np.linspace(0, 1, 11)
    ]
    _FADED, _SOLID = (
        0.06,
        0.95,
    )  # opacity of the slices that are not selected / selected

    _panels = [("scene", argo_fields), ("scene2", model_anomaly)]
    fig_3d = go.Figure()
    _surface_ids, _surface_levels = [], []
    for _scene, _fields in _panels:
        # transparent surfaces are blended in the order they are added, so add the deepest
        # slice first and the shallowest last (we look down on the stack from above)
        for _i in reversed(range(_n)):
            _field = _fields[_i]
            _surface_ids.append(len(fig_3d.data))
            _surface_levels.append(_i)
            fig_3d.add_trace(
                go.Surface(
                    x=grid_x,
                    y=grid_y,
                    # leave a hole where the Argo composite has no data
                    z=np.where(np.isfinite(_field), -float(_i), np.nan),
                    surfacecolor=_field / _scale[_i],
                    customdata=_field,
                    coloraxis="coloraxis",
                    hovertemplate="%{customdata:.2f} °C<extra></extra>",
                    lighting=dict(ambient=1, diffuse=0, specular=0),
                    opacity=_FADED,
                    scene=_scene,
                    showscale=False,
                )
            )
        # eddy outline on every slice, and the model's eddy core through all of them
        for _i in range(_n):
            fig_3d.add_trace(
                go.Scatter3d(
                    x=eddy_summary["radius_km"] * np.cos(_theta),
                    y=eddy_summary["radius_km"] * np.sin(_theta),
                    z=np.full_like(_theta, -float(_i)),
                    mode="lines",
                    line=dict(color=INSIDE_COLOR, width=4, dash="dash"),
                    hoverinfo="skip",
                    showlegend=False,
                    scene=_scene,
                )
            )
        fig_3d.add_trace(
            go.Scatter3d(
                x=[model_core_km[0]] * 2,
                y=[model_core_km[1]] * 2,
                z=[0.2, -_n + 1.0],
                mode="lines",
                line=dict(color="black", width=5),
                hoverinfo="skip",
                showlegend=False,
                scene=_scene,
            )
        )

    def _step(label, opacities, bar_vals, bar_text, bar_title):
        _opacity = [opacities.get(_i, _FADED) for _i in _surface_levels]
        return dict(
            label=label,
            method="update",
            args=[
                dict(opacity=_opacity),
                {
                    "coloraxis.colorbar.tickvals": bar_vals,
                    "coloraxis.colorbar.ticktext": bar_text,
                    "coloraxis.colorbar.title.text": bar_title,
                },
                _surface_ids,
            ],
        )

    _ticks = np.linspace(-1, 1, 5)
    _steps = [
        _step(
            f"{_d:.0f}m",
            {_i: _SOLID},
            list(_ticks),
            [f"{_t * _scale[_i]:+.2f}" for _t in _ticks],
            "Temperature anomaly (°C)",
        )
        for _i, _d in enumerate(composite_depths)
    ] + [
        _step(
            "All depths",
            {_i: 0.8 for _i in range(_n)},
            [-1, 0, 1],
            ["strongest cooling", "0", "strongest warming"],
            "Anomaly (relative to<br>each depth's range)",
        )
    ]
    _start = int(np.argmax(_scale))  # open on the slice with the strongest signal
    for _k, _level in zip(_surface_ids, _surface_levels):
        fig_3d.data[_k].opacity = _SOLID if _level == _start else _FADED

    _axis = dict(range=[-_w, _w], backgroundcolor="rgba(0,0,0,0)", gridcolor="#c8c8c8")
    _scene_layout = dict(
        xaxis=dict(title="km east", **_axis),
        yaxis=dict(title="km north", **_axis),
        zaxis=dict(
            title="Depth",
            range=[-_n + 0.5, 0.2],
            tickvals=[-float(_i) for _i in range(_n)],
            ticktext=[f"{_d:.0f}m" for _d in composite_depths],
            backgroundcolor="rgba(0,0,0,0)",
            gridcolor="#c8c8c8",
        ),
        aspectmode="manual",
        aspectratio=dict(x=1, y=1, z=1.1),
        camera=dict(eye=dict(x=1.7, y=-1.7, z=0.9)),
    )

    def _title(x, colour, name, subtitle):
        """Banner centred above one of the two 3D scenes (x = middle of the scene's domain)."""
        return dict(
            x=x,
            y=1.0,
            xref="paper",
            yref="paper",
            xanchor="center",
            yanchor="bottom",
            showarrow=False,
            font=dict(size=14),
            text=f"<b style='color:{colour}'>{name}</b><br>{subtitle}",
        )

    fig_3d.update_layout(
        height=640,
        margin=dict(l=20, r=0, t=70, b=90),
        scene=dict(domain=dict(x=[0.02, 0.44], y=[0, 1]), **_scene_layout),
        scene2=dict(domain=dict(x=[0.48, 0.90], y=[0, 1]), **_scene_layout),
        annotations=[
            _title(0.23, TRACK_COLOR, "ARGO COMPOSITE", "what the floats can see"),
            _title(0.69, _MODEL_COLOR, "OCEAN MODEL", "what is really there"),
        ],
        coloraxis=dict(
            colorscale=_colorscale,
            cmin=-1,
            cmax=1,
            colorbar=dict(
                title=dict(text="Temperature anomaly (°C)", side="right"),
                tickvals=list(_ticks),
                ticktext=[f"{_t * _scale[_start]:+.2f}" for _t in _ticks],
                len=0.6,
                x=0.97,
            ),
        ),
        sliders=[
            dict(
                active=_start,
                steps=_steps,
                currentvalue=dict(prefix="Slice depth: ", font=dict(size=14)),
                pad=dict(t=10, b=10),
                len=0.85,
                x=0.05,
            )
        ],
        template="plotly_white",
    )
    fig_3d
    return


@app.cell(hide_code=True)
def _(
    CORE_RADIUS_KM,
    argo_points,
    composite_depths,
    eddy_summary,
    mo,
    model_core_km,
    np,
    pl,
):
    # how many profiles went into each slice, and how many came near the eddy core
    _rows = []
    for _i, _depth in enumerate(composite_depths):
        _px, _py = argo_points[_i]
        _near_core = np.hypot(_px - model_core_km[0], _py - model_core_km[1])
        # argo_points are in km from the eddy centre, so the radius test is just a distance
        _in_eddy = np.hypot(_px, _py) <= eddy_summary["radius_km"]
        _rows.append(
            {
                "Depth (m)": round(float(_depth)),
                "Profiles in slice (inside and outside eddy)": len(_px),
                f"Profiles inside the eddy (within {eddy_summary['radius_km']}km of its centre)": int(
                    _in_eddy.sum()
                ),
                f"Profiles within {CORE_RADIUS_KM}km of the core": int(
                    (_near_core <= CORE_RADIUS_KM).sum()
                ),
            }
        )
    mo.vstack(
        [
            mo.md(
                "**How complete is the Argo picture?** How many profiles went into each "
                f"slice, how many of those were inside the eddy (within {eddy_summary['radius_km']}km "
                f"of its centre), and how many came within {CORE_RADIUS_KM}km of the "
                "model's eddy core."
            ),
            mo.ui.table(
                pl.DataFrame(_rows),
                selection=None,
                format_mapping={"Depth (m)": str},
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    def question_box(text, colour):
        """A textbook-style discussion panel: coloured edge and a tinted background."""
        return mo.md(text).style(
            {
                "border-left": f"6px solid {colour}",
                "border-radius": "6px",
                "padding": "0.6rem 1.2rem",
                "background": "rgba(128, 128, 128, 0.10)",
            }
        )

    mo.vstack(
        [
            mo.md(
                r"""
    ## 5) Things to think about

    This is the end of the notebook, well done for working your way through it! Now it's good to carry on thinking about the implications of this work.

    You now have a set of scientific results from an Argo campaign, plus you have had to consider a lot of experimental design questions. Listed below are some questions to prompt discussion for the next stages of your project. Maybe you won't have time to actually look into them in detail but they're useful further context to frame your discussions...
    """
            ),
            question_box(
                r"""
    **Scientific questions**:

    - What is the overall effect of the eddy on temperature and salinity of the waters contained within the eddy?
    - What implications might this have for biology in these waters?
    - This region of the Atlantic is an important zone for ocean global ocean circulation (e.g. the Atlantic Meridional Overturning Circulation/AMOC). How do the eddy's characteristics impact, or contribute, to wider ocean circulation in the area?
    - If the eddy is a long-lived "heat store", would its temperature change from year to year? How could you use a long Argo record, like the 30 years simulated here, to tell whether the eddy is warming, cooling or just staying the same?
    - The virtual floats only see what the model can show. If a real eddy also contains small filaments and swirls too small for the model to show, how might that impact the results you draw from the Argo float measurements?
                """,
                "#6186D5",
            ),
            question_box(
                r"""
    **Wider implications:**

    - Roughly what fraction of all profiles end up inside the eddy? Is it good value-for-money to run such a targeted campaign with instruments which are quite expensive in real life? Is there a balance which could be struck between cost of the campaign and quality of the scientific results?
    - Let's pretend that you are presenting your arguments to a funding organisation. How would you convince them to provide you with funding for sustained Argo float campaigns? Also, who should have the final decision? Scientists, policy makers, funders?
    - The floats drift at 1000m, near the base of the eddy's warm core. Would a shallower drifting depth keep more of them in the eddy? Why might a real Argo programme still stick to the standard 1000m?
    - Floats can't be steered once they are released. If you could choose *where* and *when* to release them, how would you use that to improve your chances of sampling the eddy?
    - We treated the eddy as one fixed circle, but real eddies wander, weaken and change with the seasons. How might that change which profiles count as "inside"?
    - This was an idealised experiment. Which of its simplifications do you think matters most for the conclusions?
                """,
                "#6186D5",
            ),
        ],
        gap=1,
    )
    return


if __name__ == "__main__":
    app.run()
