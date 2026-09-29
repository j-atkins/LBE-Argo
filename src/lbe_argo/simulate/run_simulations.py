"""Run VirtualShip Argo float simulations for every expedition in EXPEDITIONS_DIR.

Each expedition lives in its own directory (e.g. data/expeditions/1993_H1/expedition.yaml)
and is run as a separate `virtualship run` subprocess, several in parallel. Output of each
run is written to <expedition_dir>/run.log, kept as a rolling tail of the last LOG_TAIL_LINES
lines rather than a full transcript, since `virtualship run`'s progress bar emits a new line
per update.

Usage:
    python -m lbe_argo.simulate.run_simulations [--workers N] [--overwrite] [--stream] [--only 1993_H1 ...]
"""

import argparse
import re
import shutil
import subprocess
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from lbe_argo.config import EXPEDITIONS_DIR, OCEAN_DATA_DIR, PHYS_DATA_DIR

EXPEDITION_FILE = "expedition.yaml"
RESULT_FILE = Path("results") / "argo_float.parquet"
LOG_FILE = "run.log"
LOG_TAIL_LINES = 200
DEFAULT_WORKERS = 4  # each run loads ~1 year of daily ocean data; up this with care


def available_data_range(data_dir: Path) -> tuple[date, date]:
    """First and last dates of the daily ocean data files on disk."""
    dates = sorted(
        datetime.strptime(m.group(), "%Y_%m_%d").date()
        for f in data_dir.glob("*.nc")
        if (m := re.search(r"\d{4}_\d{2}_\d{2}", f.name))
    )
    if not dates:
        raise FileNotFoundError(f"No daily ocean data files found in {data_dir}")
    return dates[0], dates[-1]


def required_data_range(expedition_file: Path) -> tuple[date, date]:
    """Dates of ocean data needed: first waypoint until last waypoint + float lifetime."""
    with open(expedition_file) as f:
        expedition = yaml.safe_load(f)
    wps_in_use = [
        wp for wp in expedition["schedule"]["waypoints"] if wp.get("instrument")
    ]  # remove placeholder ports
    times = [wp["time"] for wp in wps_in_use]
    lifetime = expedition["instruments_config"]["argo_float_config"]["lifetime_days"]
    return min(times).date(), (max(times) + timedelta(days=lifetime)).date()


def reset_incomplete_run(expedition_dir: Path) -> None:
    """Remove leftovers of a crashed run.

    `virtualship run` blocks on an interactive prompt if a results/ directory exists,
    and a stale checkpoint or cache can make it refuse to rerun.
    """
    for name in ("results", "cache"):
        shutil.rmtree(expedition_dir / name, ignore_errors=True)
    (expedition_dir / "checkpoint.yaml").unlink(missing_ok=True)


def run_expedition(expedition_dir: Path, stream: bool) -> tuple[Path, bool, float]:
    """Run one expedition as a subprocess, logging its output.

    With stream=True, virtualship fetches ocean data via its normal streaming methods
    instead of reading the local files in OCEAN_DATA_DIR.
    """
    reset_incomplete_run(expedition_dir)
    start = time.time()
    log_path = expedition_dir / LOG_FILE
    tail: deque[str] = deque(maxlen=LOG_TAIL_LINES)
    cmd = ["virtualship", "run", str(expedition_dir)]
    if not stream:
        cmd += ["--from-data", str(OCEAN_DATA_DIR)]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,  # never hang on an interactive prompt
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    last_write = 0.0
    for line in (
        proc.stdout
    ):  # universal newlines splits on bare "\r" too, i.e. per progress-bar update
        tail.append(line)
        now = time.time()
        if now - last_write > 0.5:  # avoid rewriting the file on every single update
            log_path.write_text("".join(tail))
            last_write = now
    proc.wait()
    log_path.write_text("".join(tail))
    success = proc.returncode == 0 and (expedition_dir / RESULT_FILE).exists()
    return expedition_dir, success, (time.time() - start) / 60


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workers", "-j", type=int, default=DEFAULT_WORKERS)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Rerun expeditions that already have results.",
    )
    parser.add_argument(
        "--only", nargs="+", help="Expedition directory names to run, e.g. 1993_H1."
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream ocean data with virtualship's normal methods instead of using "
        "--from-data with the local files in OCEAN_DATA_DIR.",
    )
    args = parser.parse_args()

    expedition_dirs = sorted(
        p.parent for p in EXPEDITIONS_DIR.glob(f"*/{EXPEDITION_FILE}")
    )
    if args.only:
        expedition_dirs = [d for d in expedition_dirs if d.name in args.only]

    if args.stream:
        print("Streaming ocean data (not using local files)")
    else:
        data_start, data_end = available_data_range(PHYS_DATA_DIR)
        print(f"Ocean data available: {data_start} to {data_end}")

    to_run = []
    for d in expedition_dirs:
        if (d / RESULT_FILE).exists():
            if not args.overwrite:
                print(f"  skip {d.name}: already has results")
                continue
            backup_dir = d / f"results_backup_{datetime.now():%Y%m%d_%H%M%S}"
            print(
                f"  warning: {d.name} already has results, moving them to "
                f"{backup_dir.name} and continuing"
            )
            shutil.move(str(d / RESULT_FILE.parent), str(backup_dir))
        if not args.stream:
            need_start, need_end = required_data_range(d / EXPEDITION_FILE)
            if need_start < data_start or need_end > data_end:
                print(f"  skip {d.name}: needs data {need_start} to {need_end}")
                continue
        to_run.append(d)

    if not to_run:
        print("Nothing to run.")
        return 0

    print(f"\nRunning {len(to_run)} expedition(s) with {args.workers} worker(s)...")
    failed = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_expedition, d, args.stream) for d in to_run]
        for i, future in enumerate(as_completed(futures), start=1):
            d, success, minutes = future.result()
            status = "done" if success else f"FAILED (see {d / LOG_FILE})"
            print(f"[{i}/{len(to_run)}] {d.name}: {status} in {minutes:.1f} min")
            if not success:
                failed.append(d.name)

    if failed:
        print(f"\n{len(failed)} expedition(s) failed: {', '.join(failed)}")
        return 1
    print("\nAll expeditions completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
