"""Generate semi-annual VirtualShip Argo float expeditions in EXPEDITIONS_DIR.

Each half-year gets 1-2 float releases per month, at random days/times, written to
<EXPEDITIONS_DIR>/<YEAR>_H<1|2>/expedition.yaml. Floats are released at random positions
in the Norwegian Atlantic Slope Current, upstream of the Lofoten Basin (66-68°N, 0-5°E).
Existing expedition files are left alone unless --overwrite is given.

Usage:
    python -m lbe_argo.processing.make_expeditions [--years 1993 1995] [--seed 42]
        [--overwrite]
"""

import argparse
import random
from datetime import datetime

import yaml
from virtualship.models import Port

from lbe_argo.config import ARGO_CONFIG, EXPEDITIONS_DIR

# upstream deployment region along the NwASC (66-68°N, 0-5°E)
LAT_MIN, LAT_MAX = 66.0, 68.0
LON_MIN, LON_MAX = 0.0, 5.0

START_YEAR, END_YEAR = 1993, 2023


def release_times(year: int, months: range) -> list[datetime]:
    """1-2 releases per month, on distinct random days, at random quarter-hours."""
    times = []
    for month in months:
        max_days = 28 if month == 2 else (30 if month in [4, 6, 9, 11] else 31)
        days = random.sample(range(1, max_days + 1), random.choice([1, 2]))
        for day in days:
            times.append(
                datetime(
                    year,
                    month,
                    day,
                    random.randint(0, 23),
                    random.choice([0, 15, 30, 45]),
                )
            )
    return sorted(times)


def upstream_position(_time: datetime) -> tuple[float, float]:
    """Uniform random point in the upstream release region."""
    return random.uniform(LAT_MIN, LAT_MAX), random.uniform(LON_MIN, LON_MAX)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--years",
        type=int,
        nargs=2,
        default=[START_YEAR, END_YEAR],
        metavar=("FIRST", "LAST"),
    )
    parser.add_argument(
        "--seed", type=int, help="Random seed, for reproducible expeditions."
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Replace existing expedition files."
    )
    args = parser.parse_args()

    random.seed(args.seed)

    EXPEDITIONS_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for year in range(args.years[0], args.years[1] + 1):
        # two 6-month blocks per year: H1 (Jan-Jun) and H2 (Jul-Dec)
        for block, months in enumerate([range(1, 7), range(7, 13)], start=1):
            name = f"{year}_H{block}"
            yaml_path = EXPEDITIONS_DIR / name / "expedition.yaml"
            if yaml_path.exists() and not args.overwrite:
                print(f"  skip {name}: already exists (use --overwrite to replace)")
                continue

            times = release_times(year, months)
            positions = [upstream_position(t) for t in times]
            waypoints = [
                {
                    "instrument": ["ARGO_FLOAT"],
                    "location": {"latitude": round(lat, 6), "longitude": round(lon, 6)},
                    "time": t,
                }
                for t, (lat, lon) in zip(times, positions)
            ]
            # empty departure/arrival ports: ignored in the simulations but required by expedition.yaml
            waypoints.insert(0, Port(location=None, time=None).model_dump())
            waypoints.append(Port(location=None, time=None).model_dump())

            expedition = {
                "instruments_config": {"argo_float_config": ARGO_CONFIG},
                "schedule": {"waypoints": waypoints},
                "ship_config": {"ship_speed_knots": 10.0},
            }
            yaml_path.parent.mkdir(parents=True, exist_ok=True)
            with open(yaml_path, "w") as f:
                yaml.dump(expedition, f, sort_keys=False, default_flow_style=False)
            written += 1

    print(f"Wrote {written} expedition(s) to {EXPEDITIONS_DIR}")


if __name__ == "__main__":
    main()
