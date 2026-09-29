import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium", app_title="Argo floats & the Lofoten Basin Eddy")


@app.cell
def _():
    import math
    from datetime import datetime

    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    import cmocean
    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    import polars as pl
    import pyarrow.parquet as pq
    import xarray as xr
    from cartopy.geodesic import Geodesic
    from matplotlib.collections import LineCollection
    from matplotlib.colors import ListedColormap
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    from lbe_argo.config import (
        ARGO_CONFIG,
        BATHYMETRY_FPATH,
        EXPEDITIONS_DIR,
        PHYS_DATA_DIR,
    )

    return (
        ARGO_CONFIG,
        BATHYMETRY_FPATH,
        EXPEDITIONS_DIR,
        Geodesic,
        Line2D,
        LineCollection,
        ListedColormap,
        PHYS_DATA_DIR,
        Patch,
        ccrs,
        cfeature,
        cmocean,
        datetime,
        math,
        mo,
        np,
        pl,
        plt,
        pq,
        xr,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Virtual Argo floats & the Lofoten Basin Eddy

    Analysis of the VirtualShip Argo float simulations in `data/expeditions/*/results/`.
    Floats are released upstream in the Norwegian Atlantic Slope Current (66–68°N, 0–5°E)
    and drift at 1000 m, profiling 2000 m → surface every 10 days.

    The notebook picks up **whatever expeditions have finished** — rerun it as more
    simulations complete. Throughout, a float's **deployment year sets its opacity**
    (older = fainter), so the build-up across years stays readable as data accumulates.

    1. **Where do the floats go?** Bird's-eye view of every track relative to the LBE.
    2. **Do they gravitate to the eddy?** Distance to the eddy centre vs. float age.
    3. **What do they measure?** Temperature/salinity profiles inside vs. outside the eddy.
    """)
    return


@app.cell
def _():
    RESULT_FILE = "results/argo_float.parquet"
    OUTPUT_DT_S = 300  # VirtualShip Argo output interval (5 min)
    TRACK_DT_S = 6 * 3600  # subsample tracks to 6-hourly positions
    NEW_PROFILE_GAP_S = 3600  # gap in ascent samples that starts a new profile

    R_EARTH_KM = 6371.0
    MAP_EXTENT = [-5, 20, 64, 78]  # extent of the downloaded ocean data
    # upstream deployment corridor, see lbe_argo/processing/make_expeditions.py
    DEPLOY_BOX = dict(lat_min=66.0, lat_max=68.0, lon_min=0.0, lon_max=5.0)
    # observed (quasi-permanent) LBE centre, approx. — adjustable below
    LBE_CENTRE_DEFAULT = dict(lat=69.8, lon=3.5)

    TRACK_COLOR = "#1c5cab"
    INSIDE_COLOR = "#eb6834"  # warm-core eddy -> orange
    OUTSIDE_COLOR = "#2a78d6"
    INK = "#0b0b0b"
    INK_MUTED = "#52514e"
    ALPHA_RANGE = (0.3, 0.95)  # oldest -> newest deployment year
    return (
        ALPHA_RANGE,
        DEPLOY_BOX,
        INK,
        INK_MUTED,
        INSIDE_COLOR,
        LBE_CENTRE_DEFAULT,
        MAP_EXTENT,
        NEW_PROFILE_GAP_S,
        OUTPUT_DT_S,
        OUTSIDE_COLOR,
        RESULT_FILE,
        R_EARTH_KM,
        TRACK_COLOR,
        TRACK_DT_S,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Load simulation output

    Each `argo_float.parquet` holds every float state at 5-minute resolution
    (~1M rows per expedition), so only what is needed is read:

    - **tracks**: 6-hourly positions,
    - **profile samples**: the ascent phase (`cycle_phase == 3`), where T/S are sampled,
    - **deployments**: first position/time of each float.

    Times are stored as *seconds since* the first deployment of each expedition, so
    they're decoded per file. Files that can't be read yet (a simulation still writing)
    are skipped.
    """)
    return


@app.cell
def _(
    EXPEDITIONS_DIR,
    NEW_PROFILE_GAP_S,
    OUTPUT_DT_S,
    RESULT_FILE,
    TRACK_DT_S,
    datetime,
    pl,
    pq,
):
    def time_origin(path):
        """Decode the CF 'seconds since ...' origin of the parquet `t` column."""
        units = pq.read_schema(path).field("t").metadata[b"units"].decode()
        return datetime.fromisoformat(units.split("since", 1)[1].strip())

    def load_expedition(path):
        expedition = path.parent.parent.name
        origin = time_origin(path)
        lf = (
            pl.scan_parquet(path)
            .select("t", "z", "y", "x", "particle_id", "cycle_phase", "temperature", "salinity")
            .with_columns(
                float_id=pl.lit(f"{expedition}_") + pl.col("particle_id").cast(pl.String).str.zfill(2),
                time=pl.lit(origin) + pl.duration(milliseconds=(pl.col("t") * 1000).cast(pl.Int64)),
            )
        )
        deployments = (
            lf.sort("t")
            .group_by("float_id")
            .agg(
                deploy_time=pl.col("time").first(),
                end_time=pl.col("time").last(),
                lon0=pl.col("x").first(),
                lat0=pl.col("y").first(),
            )
            .with_columns(expedition=pl.lit(expedition))
        )
        tracks = lf.filter((pl.col("t") % TRACK_DT_S) < OUTPUT_DT_S).select("float_id", "time", "x", "y")
        samples = lf.filter(
            (pl.col("cycle_phase") == 3)
            & pl.col("temperature").is_finite()
            & pl.col("salinity").is_finite()
            # samples from land/masked cells come back as exactly 0
            & ~((pl.col("temperature") == 0) & (pl.col("salinity") == 0))
            & (pl.col("z") < 0)
        ).select("float_id", "time", "x", "y", "z", "temperature", "salinity")
        return pl.collect_all([deployments, tracks, samples])

    result_paths = sorted(EXPEDITIONS_DIR.glob(f"*/{RESULT_FILE}"))
    _loaded, skipped = [], []
    for _path in result_paths:
        try:
            _loaded.append(load_expedition(_path))
        except Exception as err:  # e.g. parquet footer missing while a run is in progress
            skipped.append(f"{_path.parent.parent.name} ({type(err).__name__})")

    deployments_all = pl.concat([d for d, _, _ in _loaded]).with_columns(
        deploy_year=pl.col("deploy_time").dt.year()
    )
    _deploy_info = deployments_all.select("float_id", "deploy_time", "deploy_year")
    _days_since = ((pl.col("time") - pl.col("deploy_time")).dt.total_seconds() / 86400).alias(
        "days_since_deploy"
    )

    tracks_all = (
        pl.concat([t for _, t, _ in _loaded])
        .join(_deploy_info, on="float_id")
        .with_columns(_days_since)
        .sort("float_id", "time")
    )

    samples_all = (
        pl.concat([s for _, _, s in _loaded])
        .join(_deploy_info, on="float_id")
        .with_columns(_days_since, depth=-pl.col("z"))
        .sort("float_id", "time")
        .with_columns(
            profile_num=(pl.col("time").diff().dt.total_seconds() > NEW_PROFILE_GAP_S)
            .fill_null(False)
            .cum_sum()
            .over("float_id")
        )
        .with_columns(profile_id=pl.col("float_id") + "_p" + pl.col("profile_num").cast(pl.String))
    )
    return deployments_all, result_paths, samples_all, skipped, tracks_all


@app.cell(hide_code=True)
def _(deployments_all, mo, result_paths, samples_all, skipped):
    _years = sorted(deployments_all["deploy_year"].unique())
    _msg = (
        f"Loaded **{len(result_paths) - len(skipped)}** expedition(s) → "
        f"**{deployments_all.height}** floats deployed in "
        f"**{', '.join(map(str, _years))}**, "
        f"**{samples_all['profile_id'].n_unique():,}** profiles."
    )
    if skipped:
        _msg += f"\n\nSkipped (unreadable/incomplete): {', '.join(skipped)}"
    mo.callout(mo.md(_msg), kind="warn" if skipped else "info")
    return


@app.cell
def _(BATHYMETRY_FPATH, MAP_EXTENT, PHYS_DATA_DIR, deployments_all, xr):
    # background fields for the map
    _lon_min, _lon_max, _lat_min, _lat_max = MAP_EXTENT
    _region = dict(latitude=slice(_lat_min, _lat_max), longitude=slice(_lon_min, _lon_max))

    bathymetry = xr.open_dataset(BATHYMETRY_FPATH).deptho.sel(**_region).load()  # NaN on land

    # time-mean model temperature at ~500 m over the deployment years, where the warm LBE core
    # sits. Every 10th daily file is plenty for a climatology and keeps this fast.
    _years = set(deployments_all["deploy_year"].unique().to_list())
    _files = sorted(f for f in PHYS_DATA_DIR.glob("*.nc") if any(f"_{y}_" in f.name for y in _years))
    with xr.open_mfdataset(
        _files[::10], combine="by_coords", data_vars="minimal", coords="minimal", compat="override"
    ) as _ds:
        mean_temp_500m = _ds.thetao_glor.sel(depth=500, method="nearest").mean("time").sel(**_region).load()
    return bathymetry, mean_temp_500m


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Controls

    The eddy centre defaults to the LBE's observed, quasi-permanent position.
    Note the ocean model is ¼° (~10 × 28 km here), coarser than the eddy core
    (~15–20 km radius), so the modelled eddy is smoothed and may sit somewhat off the
    observed position — switch the map background to the model's mean 500 m temperature
    to check where its warm core is, and move the centre/radius to suit.
    """)
    return


@app.cell
def _(ARGO_CONFIG, LBE_CENTRE_DEFAULT, deployments_all, mo):
    _years = [str(y) for y in sorted(deployments_all["deploy_year"].unique())]
    year_select = mo.ui.multiselect(options=_years, value=_years, label="Deployment years")
    truncate_lifetime = mo.ui.checkbox(
        value=True, label=f"Cut tracks at float lifetime ({ARGO_CONFIG['lifetime_days']:.0f} days)"
    )
    centre_lat = mo.ui.number(
        start=66, stop=73, step=0.05, value=LBE_CENTRE_DEFAULT["lat"], label="Eddy centre lat (°N)"
    )
    centre_lon = mo.ui.number(
        start=-4, stop=12, step=0.05, value=LBE_CENTRE_DEFAULT["lon"], label="Eddy centre lon (°E)"
    )
    eddy_radius = mo.ui.slider(
        start=10, stop=200, step=5, value=50, label="'Inside eddy' radius (km)", show_value=True
    )
    map_background = mo.ui.dropdown(
        options=["Bathymetry", "Model mean temperature @ 500 m"], value="Bathymetry", label="Map background"
    )
    depth_on_y = mo.ui.switch(value=False, label="Depth on y-axis (oceanographic convention)")

    mo.vstack(
        [
            mo.hstack([year_select, truncate_lifetime], justify="start", gap=2),
            mo.hstack([centre_lat, centre_lon, eddy_radius], justify="start", gap=2),
            mo.hstack([map_background, depth_on_y], justify="start", gap=2),
        ]
    )
    return (
        centre_lat,
        centre_lon,
        depth_on_y,
        eddy_radius,
        map_background,
        truncate_lifetime,
        year_select,
    )


@app.cell
def _(
    ALPHA_RANGE,
    ARGO_CONFIG,
    R_EARTH_KM,
    centre_lat,
    centre_lon,
    deployments_all,
    eddy_radius,
    math,
    np,
    pl,
    samples_all,
    tracks_all,
    truncate_lifetime,
    year_select,
):
    def distance_km(lat_col, lon_col, lat0, lon0):
        """Great-circle (haversine) distance from (lat0, lon0) as a polars expression."""
        phi, lam = pl.col(lat_col).radians(), pl.col(lon_col).radians()
        phi0, lam0 = math.radians(lat0), math.radians(lon0)
        a = ((phi - phi0) / 2).sin() ** 2 + phi.cos() * math.cos(phi0) * ((lam - lam0) / 2).sin() ** 2
        return 2 * R_EARTH_KM * a.sqrt().arcsin()

    # opacity per deployment year, fixed over *all* loaded years so filtering doesn't restyle
    _all_years = sorted(deployments_all["deploy_year"].unique())
    _alphas = np.linspace(*ALPHA_RANGE, len(_all_years)) if len(_all_years) > 1 else [ALPHA_RANGE[1]]
    year_alpha = dict(zip(_all_years, _alphas))

    eddy_lat, eddy_lon, radius_km = centre_lat.value, centre_lon.value, eddy_radius.value
    _years = [int(y) for y in year_select.value]
    _keep = pl.col("deploy_year").is_in(_years)
    if truncate_lifetime.value:
        _keep &= pl.col("days_since_deploy") <= ARGO_CONFIG["lifetime_days"]

    deployments = deployments_all.filter(pl.col("deploy_year").is_in(_years))
    tracks = tracks_all.filter(_keep).with_columns(dist_km=distance_km("y", "x", eddy_lat, eddy_lon))
    samples = samples_all.filter(_keep)

    # one row per profile, located at the mean position of its ascent
    profiles = (
        samples.group_by("profile_id", maintain_order=True)
        .agg(
            pl.col("float_id", "deploy_year").first(),
            pl.col("time").last(),
            pl.col("days_since_deploy").last(),
            pl.col("x", "y").mean(),
        )
        .with_columns(dist_km=distance_km("y", "x", eddy_lat, eddy_lon))
        .with_columns(inside=pl.col("dist_km") <= radius_km)
    )
    samples = samples.join(profiles.select("profile_id", "inside", "dist_km"), on="profile_id")
    return (
        deployments,
        eddy_lat,
        eddy_lon,
        profiles,
        radius_km,
        samples,
        tracks,
        year_alpha,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1 · Where do the floats go?

    Every float track (6-hourly surface/drift positions), opacity by deployment year.
    Black dots mark releases; the dashed box is the deployment corridor and the orange
    circle the "inside eddy" region used below.
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
    TRACK_COLOR,
    bathymetry,
    ccrs,
    cfeature,
    cmocean,
    deployments,
    eddy_lat,
    eddy_lon,
    map_background,
    mean_temp_500m,
    np,
    pl,
    plt,
    radius_km,
    tracks,
    year_alpha,
):
    _proj = ccrs.NorthPolarStereo(central_longitude=7.5)
    _pc = ccrs.PlateCarree()
    fig_map, _ax = plt.subplots(figsize=(9, 8), subplot_kw=dict(projection=_proj))
    _ax.set_extent(MAP_EXTENT, crs=_pc)

    # background
    _lon, _lat = bathymetry.longitude, bathymetry.latitude
    def _pale(cmap, strength):
        """Opaque, washed-out copy of a colormap (translucent cells leave seams once reprojected)."""
        rgb = cmap(np.linspace(0, 1, 256))[:, :3]
        return ListedColormap(strength * rgb + (1 - strength))

    _mesh_kw = dict(transform=_pc, zorder=0, shading="auto", rasterized=True)
    if map_background.value == "Bathymetry":
        _mesh = _ax.pcolormesh(_lon, _lat, bathymetry, cmap=_pale(cmocean.cm.deep, 0.45), vmin=0, vmax=5000, **_mesh_kw)
        _cbar_label = "Depth (m)"
    else:
        _mesh = _ax.pcolormesh(
            mean_temp_500m.longitude, mean_temp_500m.latitude, mean_temp_500m,
            cmap=_pale(cmocean.cm.thermal, 0.55), **_mesh_kw,
        )
        _cbar_label = "Model mean temperature @ 500 m (°C)"
    _ax.contour(
        _lon, _lat, bathymetry, levels=[1000, 2000, 3000], colors=INK_MUTED, linewidths=0.4, alpha=0.6, transform=_pc
    )
    _ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#d9d8d3", zorder=1)
    _ax.coastlines(resolution="50m", linewidth=0.6, color=INK_MUTED, zorder=2)
    fig_map.colorbar(_mesh, ax=_ax, shrink=0.6, pad=0.02, label=_cbar_label)

    # tracks, one LineCollection so thousands of floats stay fast
    _per_float = tracks.group_by("float_id", maintain_order=True).agg("x", "y", pl.col("deploy_year").first())
    _segments, _colors = [], []
    for _xs, _ys, _year in _per_float.select("x", "y", "deploy_year").iter_rows():
        _pts = _proj.transform_points(_pc, np.asarray(_xs), np.asarray(_ys))[:, :2]
        _segments.append(_pts)
        _colors.append((*plt.matplotlib.colors.to_rgb(TRACK_COLOR), year_alpha[_year]))
    _ax.add_collection(LineCollection(_segments, colors=_colors, linewidths=0.9, zorder=3))

    _ax.scatter(deployments["lon0"], deployments["lat0"], s=9, color=INK, transform=_pc, zorder=4)
    _box = DEPLOY_BOX
    _ax.plot(
        [_box["lon_min"], _box["lon_max"], _box["lon_max"], _box["lon_min"], _box["lon_min"]],
        [_box["lat_min"], _box["lat_min"], _box["lat_max"], _box["lat_max"], _box["lat_min"]],
        color=INK,
        linestyle="--",
        linewidth=1,
        transform=_pc,
        zorder=4,
    )

    _circle = Geodesic().circle(eddy_lon, eddy_lat, radius_km * 1e3, n_samples=120)
    _ax.fill(_circle[:, 0], _circle[:, 1], color=INSIDE_COLOR, alpha=0.15, transform=_pc, zorder=5)
    _ax.plot(_circle[:, 0], _circle[:, 1], color=INSIDE_COLOR, linewidth=2, linestyle="--", transform=_pc, zorder=5)
    _ax.plot(eddy_lon, eddy_lat, marker="+", color=INSIDE_COLOR, markersize=10, mew=2, transform=_pc, zorder=5)

    _gl = _ax.gridlines(draw_labels=True, linewidth=0.3, color=INK_MUTED, alpha=0.5)
    _gl.top_labels = _gl.right_labels = False

    _handles = [
        Line2D([], [], color=TRACK_COLOR, alpha=year_alpha[y], lw=2, label=f"Deployed {y}")
        for y in sorted(deployments["deploy_year"].unique())
    ] + [
        Line2D([], [], marker="o", color=INK, lw=0, markersize=4, label="Release"),
        Patch(facecolor=INSIDE_COLOR, alpha=0.3, edgecolor=INSIDE_COLOR, label=f"LBE (r = {radius_km} km)"),
    ]
    _ax.legend(handles=_handles, loc="upper left", fontsize=8, framealpha=0.9)
    _ax.set_title("Virtual Argo float tracks & the Lofoten Basin Eddy", loc="left", fontsize=11)
    fig_map.tight_layout()
    fig_map
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2 · Do the floats gravitate to the eddy?

    Distance of each float from the eddy centre as it ages (thin lines, opacity by
    deployment year; bold = median over active floats), and the share of active floats
    that are inside the eddy radius on each day.
    """)
    return


@app.cell
def _(INK, INK_MUTED, INSIDE_COLOR, TRACK_COLOR, np, pl, plt, radius_km, tracks, year_alpha):
    _daily = (
        tracks.with_columns(day=pl.col("days_since_deploy").floor())
        .group_by("day")
        .agg(
            median_km=pl.col("dist_km").median(),
            frac_inside=(pl.col("dist_km") <= radius_km).mean(),
            n_floats=pl.col("float_id").n_unique(),
        )
        .filter(pl.col("n_floats") >= 3)
        .sort("day")
    )

    fig_gravity, (_ax_d, _ax_f) = plt.subplots(
        2, 1, figsize=(9, 6), sharex=True, gridspec_kw=dict(height_ratios=[2, 1])
    )
    for (_year,), _grp in tracks.group_by("deploy_year"):
        _a = year_alpha[_year] * 0.5  # thinner/lighter than the map: many overlapping lines
        for (_fid,), _f in _grp.group_by("float_id"):
            _ax_d.plot(_f["days_since_deploy"], _f["dist_km"], color=TRACK_COLOR, alpha=_a, lw=0.6)
    _ax_d.plot(_daily["day"], _daily["median_km"], color=INK, lw=2, label="Median (active floats)")
    _ax_d.axhline(radius_km, color=INSIDE_COLOR, lw=2, ls="--", label=f"Eddy radius ({radius_km} km)")
    _ax_d.set_ylabel("Distance to eddy centre (km)")
    _ax_d.set_ylim(bottom=0)
    _ax_d.legend(loc="upper right", fontsize=8)

    _ax_f.fill_between(_daily["day"], 0, 100 * _daily["frac_inside"], color=INSIDE_COLOR, alpha=0.15, lw=0)
    _ax_f.plot(_daily["day"], 100 * _daily["frac_inside"], color=INSIDE_COLOR, lw=2)
    _ax_f.set_ylabel("Floats inside\neddy (%)")
    _ax_f.set_xlabel("Days since deployment")
    _ax_f.set_ylim(0, max(5, 100 * np.nanmax(_daily["frac_inside"].to_numpy(), initial=0) * 1.15))

    for _ax in (_ax_d, _ax_f):
        _ax.grid(color=INK_MUTED, alpha=0.15, lw=0.5)
        _ax.spines[["top", "right"]].set_visible(False)
    fig_gravity.tight_layout()
    fig_gravity
    return


@app.cell(hide_code=True)
def _(deployments, mo, pl, profiles, radius_km, tracks):
    _by_year = (
        profiles.group_by("deploy_year")
        .agg(
            profiles=pl.len(),
            inside=pl.col("inside").sum(),
        )
        .join(
            tracks.group_by("deploy_year").agg(
                float_days_inside_pct=((pl.col("dist_km") <= radius_km).mean() * 100).round(1),
                ever_inside=pl.col("float_id").filter(pl.col("dist_km") <= radius_km).n_unique(),
            ),
            on="deploy_year",
        )
        .join(deployments.group_by("deploy_year").agg(floats=pl.len()), on="deploy_year")
        .with_columns(inside_pct=(100 * pl.col("inside") / pl.col("profiles")).round(1))
        .select(
            pl.col("deploy_year").alias("Deployment year"),
            pl.col("floats").alias("Floats"),
            pl.col("ever_inside").alias("Floats ever inside eddy"),
            pl.col("float_days_inside_pct").alias("Float-time inside (%)"),
            pl.col("profiles").alias("Profiles"),
            pl.col("inside").alias("Profiles inside eddy"),
            pl.col("inside_pct").alias("Profiles inside (%)"),
        )
        .sort("Deployment year")
    )
    mo.vstack([mo.md(f"**Summary by deployment year** (eddy radius {radius_km} km)"), mo.ui.table(_by_year, selection=None)])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3 · Profiles inside vs. outside the eddy

    Every profile collected during ascent (2000 m → surface), split by whether the
    profile was taken within the eddy radius. Opacity by deployment year; black line =
    median over profiles in 25 m depth bins.
    """)
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
            df.with_columns(depth_bin=(pl.col("depth") / bin_m).floor() * bin_m + bin_m / 2)
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
    depth_on_y,
    pl,
    plt,
    samples,
    year_alpha,
):
    def _xy(depth, value):
        """Order (x, y) according to the depth-axis toggle."""
        return (value, depth) if depth_on_y.value else (depth, value)

    _groups = {
        "Inside eddy": (samples.filter(pl.col("inside")), INSIDE_COLOR),
        "Outside eddy": (samples.filter(~pl.col("inside")), OUTSIDE_COLOR),
    }
    # depth axis shared across all panels, each variable's axis shared along its row
    _share = dict(sharex="row", sharey=True) if depth_on_y.value else dict(sharex=True, sharey="row")
    fig_profiles, _axes = plt.subplots(len(VARIABLES), 2, figsize=(10, 7.5), squeeze=False, **_share)

    for _col, (_title, (_df, _color)) in enumerate(_groups.items()):
        _per_profile = _df.group_by("profile_id", maintain_order=True).agg(
            "depth", *VARIABLES, pl.col("deploy_year").first()
        )
        _rgba = [(*plt.matplotlib.colors.to_rgb(_color), year_alpha[y] * 0.6) for y in _per_profile["deploy_year"]]
        for _row, (_var, _label) in enumerate(VARIABLES.items()):
            _ax = _axes[_row, _col]
            _segments = [list(zip(*_xy(d, v))) for d, v in zip(_per_profile["depth"], _per_profile[_var])]
            _ax.add_collection(LineCollection(_segments, colors=_rgba, linewidths=0.6))
            if _df.height:
                _med = binned_profile(_df, _var)
                _ax.plot(*_xy(_med["depth_bin"], _med["median"]), color=INK, lw=2)
            else:
                _ax.text(0.5, 0.5, "No profiles", transform=_ax.transAxes, ha="center", color=INK_MUTED)
            _ax.autoscale_view()
            _ax.grid(color=INK_MUTED, alpha=0.15, lw=0.5)
            _ax.spines[["top", "right"]].set_visible(False)
            _depth_label, _var_label = "Depth (m)", _label
            _ax.set_xlabel(_xy(_depth_label, _var_label)[0] if _row == len(VARIABLES) - 1 or depth_on_y.value else "")
            if _col == 0:
                _ax.set_ylabel(_xy(_depth_label, _var_label)[1])
        _axes[0, _col].set_title(f"{_title}  ·  {_per_profile.height:,} profiles", loc="left", fontsize=10)

    if depth_on_y.value:
        for _ax in _axes.flat:
            _ax.set_ylim(2000, 0)
    fig_profiles.tight_layout()
    fig_profiles
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Inside − outside comparison

    Median profile (line) and inter-quartile range (band) for each group.
    """)
    return


@app.cell
def _(
    INK_MUTED,
    INSIDE_COLOR,
    OUTSIDE_COLOR,
    VARIABLES,
    binned_profile,
    depth_on_y,
    pl,
    plt,
    samples,
):
    fig_compare, _axes = plt.subplots(1, len(VARIABLES), figsize=(10, 4.2), squeeze=False)
    for _ax, (_var, _label) in zip(_axes[0], VARIABLES.items()):
        for _name, _mask, _color in [
            ("Inside eddy", pl.col("inside"), INSIDE_COLOR),
            ("Outside eddy", ~pl.col("inside"), OUTSIDE_COLOR),
        ]:
            _stats = binned_profile(samples.filter(_mask), _var)
            if _stats.height == 0:
                continue
            _n = samples.filter(_mask)["profile_id"].n_unique()
            if depth_on_y.value:
                _ax.fill_betweenx(_stats["depth_bin"], _stats["q25"], _stats["q75"], color=_color, alpha=0.15, lw=0)
                _ax.plot(_stats["median"], _stats["depth_bin"], color=_color, lw=2, label=f"{_name} (n={_n:,})")
            else:
                _ax.fill_between(_stats["depth_bin"], _stats["q25"], _stats["q75"], color=_color, alpha=0.15, lw=0)
                _ax.plot(_stats["depth_bin"], _stats["median"], color=_color, lw=2, label=f"{_name} (n={_n:,})")
        if depth_on_y.value:
            _ax.set_ylim(2000, 0)
            _ax.set(xlabel=_label, ylabel="Depth (m)")
        else:
            _ax.set(xlabel="Depth (m)", ylabel=_label)
        _ax.grid(color=INK_MUTED, alpha=0.15, lw=0.5)
        _ax.spines[["top", "right"]].set_visible(False)
        _ax.legend(fontsize=8)
    fig_compare.tight_layout()
    fig_compare
    return


if __name__ == "__main__":
    app.run()
