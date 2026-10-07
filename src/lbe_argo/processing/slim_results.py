"""Slim copies of the VirtualShip Argo float output, for fast analysis.

Each `results/argo_float.parquet` holds every float state at 5-minute resolution
(~1.5M rows, ~500 MB per expedition), but the analysis notebook only needs:

- deployments: first position/time of each float,
- tracks: 6-hourly positions,
- samples: the ascent phase (`cycle_phase == 3`), where T/S are sampled.

These are written to `results/slim/{deployments,tracks,samples}.parquet` (a few MB in
total), with times decoded to datetimes. `load_slim` rebuilds them whenever they are
missing or older than the full output, so the notebook builds the cache on first use;
run this module to build it for every expedition up front.

Usage:
    python -m lbe_argo.processing.slim_results [--overwrite]
"""

import argparse
import functools
from datetime import datetime
from pathlib import Path

import polars as pl
import pyarrow.parquet as pq
import yaml

from lbe_argo.bundled import bundled_file
from lbe_argo.config import BUNDLE_DIR, EXPEDITIONS_DIR, is_expedition

RESULT_FILE = Path("results") / "argo_float.parquet"
SLIM_DIR = Path("results") / "slim"
TABLES = ("deployments", "tracks", "samples")

OUTPUT_DT_S = 300  # VirtualShip Argo output interval (5 min)
TRACK_DT_S = 6 * 3600  # subsample tracks to 6-hourly positions


def time_origin(path: Path) -> datetime:
    """Decode the CF 'seconds since ...' origin of the parquet `t` column."""
    units = pq.read_schema(path).field("t").metadata[b"units"].decode()
    return datetime.fromisoformat(units.split("since", 1)[1].strip())


def slim_paths(expedition_dir: Path) -> dict[str, Path]:
    return {name: expedition_dir / SLIM_DIR / f"{name}.parquet" for name in TABLES}


def is_fresh(expedition_dir: Path) -> bool:
    """Slim tables exist and are newer than the full simulation output.

    Without the full output (e.g. a clone of the repo, which only has the slim tables),
    existing slim tables count as fresh.
    """
    source = expedition_dir / RESULT_FILE
    source_mtime = source.stat().st_mtime if source.exists() else 0.0
    return all(
        p.exists() and p.stat().st_mtime >= source_mtime
        for p in slim_paths(expedition_dir).values()
    )


def build_slim(expedition_dir: Path) -> dict[str, pl.DataFrame]:
    """Read the full output once and write the slim tables."""
    path = expedition_dir / RESULT_FILE
    origin = time_origin(path)
    lf = (
        pl.scan_parquet(path)
        .select(
            "t", "z", "y", "x", "particle_id", "cycle_phase", "temperature", "salinity"
        )
        .with_columns(
            time=pl.lit(origin)
            + pl.duration(milliseconds=(pl.col("t") * 1000).cast(pl.Int64))
        )
    )
    deployments = (
        lf.sort("t")
        .group_by("particle_id")
        .agg(
            deploy_time=pl.col("time").first(),
            end_time=pl.col("time").last(),
            lon0=pl.col("x").first(),
            lat0=pl.col("y").first(),
        )
        .sort("particle_id")
    )
    tracks = lf.filter((pl.col("t") % TRACK_DT_S) < OUTPUT_DT_S).select(
        "particle_id", "time", "x", "y"
    )
    samples = lf.filter(
        (pl.col("cycle_phase") == 3)
        & pl.col("temperature").is_finite()
        & pl.col("salinity").is_finite()
        # samples from land/masked cells come back as exactly 0
        & ~((pl.col("temperature") == 0) & (pl.col("salinity") == 0))
        & (pl.col("z") < 0)
    ).select("particle_id", "time", "x", "y", "z", "temperature", "salinity")
    tables = dict(zip(TABLES, pl.collect_all([deployments, tracks, samples])))

    (expedition_dir / SLIM_DIR).mkdir(parents=True, exist_ok=True)
    for name, out in slim_paths(expedition_dir).items():
        tables[name].write_parquet(out)
    return tables


@functools.cache
def bundled_tables() -> dict[str, pl.DataFrame]:
    """Slim tables of every expedition, in one table each with an `expedition` column."""
    return {name: pl.read_parquet(bundled_file(f"{name}.parquet")) for name in TABLES}


def load_slim(expedition_dir: Path) -> dict[str, pl.DataFrame]:
    """Slim tables of one expedition.

    They are (re)built from the full output if that exists and is newer. Without the full
    output (e.g. in a clone of the repo) the slim tables on disk are used, and without
    those the bundled tables (downloaded if need be).
    """
    if (expedition_dir / RESULT_FILE).exists() and not is_fresh(expedition_dir):
        return build_slim(expedition_dir)
    paths = slim_paths(expedition_dir)
    if all(p.exists() for p in paths.values()):
        return {name: pl.read_parquet(p) for name, p in paths.items()}
    return {
        name: df.filter(pl.col("expedition") == expedition_dir.name).drop("expedition")
        for name, df in bundled_tables().items()
    }


def n_floats(expedition_dir: Path) -> int:
    """Number of floats an expedition releases."""
    deployments = slim_paths(expedition_dir)["deployments"]
    if deployments.exists():
        return pl.read_parquet(deployments).height
    with open(expedition_dir / "expedition.yaml") as f:
        expedition = yaml.safe_load(f)
    return sum(1 for wp in expedition["schedule"]["waypoints"] if wp.get("instrument"))


def local_expeditions() -> list[Path]:
    """Expedition directories on disk with simulation output (full or slim)."""
    return sorted(
        {
            p.parents[len(pattern.parts) - 1]
            for pattern in (RESULT_FILE, SLIM_DIR / "deployments.parquet")
            for p in EXPEDITIONS_DIR.glob(f"*/{pattern}")
            if is_expedition(p.parents[len(pattern.parts) - 1])
        }
    )


def list_available() -> pl.DataFrame:
    """Every expedition with simulation output: expedition, expedition_dir, year, n_floats.

    These are the expeditions with output on disk or, without any, those in the bundled tables.
    """
    rows = [(d.name, n_floats(d)) for d in local_expeditions()]
    if not rows:
        counts = (
            bundled_tables()["deployments"]
            .group_by("expedition")
            .len()
            .sort("expedition")
        )
        rows = list(counts.iter_rows())
    return pl.DataFrame(
        [
            dict(
                expedition=name,
                expedition_dir=str(EXPEDITIONS_DIR / name),
                year=int(name[:4]),
                n_floats=n,
            )
            for name, n in rows
        ],
        schema=dict(
            expedition=pl.String,
            expedition_dir=pl.String,
            year=pl.Int64,
            n_floats=pl.Int64,
        ),
    )


def build_bundle() -> None:
    """Merge the slim tables of every expedition into the bundled tables."""
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    tables: dict[str, list[pl.DataFrame]] = {name: [] for name in TABLES}
    expedition_dirs = local_expeditions()
    if not expedition_dirs:
        raise SystemExit(f"No simulation output found in {EXPEDITIONS_DIR}")
    for d in expedition_dirs:
        for name, df in load_slim(d).items():
            tables[name].append(df.with_columns(expedition=pl.lit(d.name)))
    for name, frames in tables.items():
        path = BUNDLE_DIR / f"{name}.parquet"
        pl.concat(frames).write_parquet(path, compression="zstd")
        print(f"Wrote {path} ({path.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--overwrite", action="store_true", help="Rebuild slim tables that are fresh."
    )
    args = parser.parse_args()

    expedition_dirs = sorted(
        p.parent.parent
        for p in EXPEDITIONS_DIR.glob(f"*/{RESULT_FILE}")
        if is_expedition(p.parent.parent)
    )
    for i, d in enumerate(expedition_dirs, start=1):
        if is_fresh(d) and not args.overwrite:
            print(f"[{i}/{len(expedition_dirs)}] {d.name}: up to date")
            continue
        try:
            build_slim(d)
            print(f"[{i}/{len(expedition_dirs)}] {d.name}: built")
        except (
            Exception
        ) as err:  # e.g. parquet footer missing while a run is in progress
            print(
                f"[{i}/{len(expedition_dirs)}] {d.name}: skipped ({type(err).__name__})"
            )


if __name__ == "__main__":
    main()
