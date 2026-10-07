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
from datetime import datetime
from pathlib import Path

import polars as pl
import pyarrow.parquet as pq

from lbe_argo.config import EXPEDITIONS_DIR, is_expedition

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
    """Slim tables exist and are newer than the full simulation output."""
    source_mtime = (expedition_dir / RESULT_FILE).stat().st_mtime
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


def load_slim(expedition_dir: Path) -> dict[str, pl.DataFrame]:
    """Slim tables of one expedition, (re)building them from the full output if needed."""
    if not is_fresh(expedition_dir):
        return build_slim(expedition_dir)
    return {name: pl.read_parquet(p) for name, p in slim_paths(expedition_dir).items()}


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
        except Exception as err:  # e.g. parquet footer missing while a run is in progress
            print(f"[{i}/{len(expedition_dirs)}] {d.name}: skipped ({type(err).__name__})")


if __name__ == "__main__":
    main()
