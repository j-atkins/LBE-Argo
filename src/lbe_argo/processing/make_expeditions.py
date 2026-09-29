from virtualship.models import Port
import random
from datetime import datetime
import yaml
from lbe_argo.config import EXPEDITIONS_DIR, ARGO_CONFIG

# Define upstream deployment region along NwASC (66-68°N, 0-5°E)
LAT_MIN, LAT_MAX = 66.0, 68.0
LON_MIN, LON_MAX = 0.0, 5.0

# Ensure base expeditions directory exists
EXPEDITIONS_DIR.mkdir(parents=True, exist_ok=True)

start_year, end_year = 1993, 2023
total_files = 0
total_waypoints = 0

for year in range(start_year, end_year + 1):
    # Two 6-month blocks per year: Block 1 (Jan-Jun) and Block 2 (Jul-Dec)
    for block_num, month_range in enumerate([range(1, 7), range(7, 13)], start=1):
        waypoints = []
        used_days = set()  # Track (month, day) pairs already selected in this block

        for month in month_range:
            num_releases = random.choice([1, 2])
            max_days = 28 if month == 2 else (30 if month in [4, 6, 9, 11] else 31)

            for _ in range(num_releases):
                # Determine available unused days in the current month
                available_days = [
                    d for d in range(1, max_days + 1) if (month, d) not in used_days
                ]

                # If all days in this month are exhausted, skip further releases
                if not available_days:
                    break

                day = random.choice(available_days)
                used_days.add((month, day))  # Mark this day as taken

                hour = random.randint(0, 23)
                minute = random.choice([0, 15, 30, 45])

                dt = datetime(year, month, day, hour, minute)

                # Randomize coordinate along upstream corridor
                lat = round(random.uniform(LAT_MIN, LAT_MAX), 6)
                lon = round(random.uniform(LON_MIN, LON_MAX), 6)

                waypoints.append(
                    {
                        "instrument": ["ARGO_FLOAT"],
                        "location": {"latitude": lat, "longitude": lon},
                        "time": dt,
                    }
                )

        # Sort waypoints chronologically by datetime
        waypoints.sort(key=lambda x: x["time"])

        # insert and append empty Port waypoints
        # ignored in simulations but necessary for expeditiom.yaml structure
        waypoints.insert(0, Port(location=None, time=None).model_dump())  # departure
        waypoints.append(Port(location=None, time=None).model_dump())  # arrival

        # Build semi-annual expedition YAML structure
        expedition_data = {
            "instruments_config": {"argo_float_config": ARGO_CONFIG},
            "schedule": {"waypoints": waypoints},
            "ship_config": {"ship_speed_knots": 10.0},
        }

        # Create subdirectory with block metadata: e.g. "data/expeditions/1993_H1/"
        block_dir = EXPEDITIONS_DIR / f"{year}_H{block_num}"
        block_dir.mkdir(parents=True, exist_ok=True)

        # Save as expedition.yaml inside the metadata folder
        yaml_path = block_dir / "expedition.yaml"

        with open(yaml_path, "w") as f:
            yaml.dump(expedition_data, f, sort_keys=False, default_flow_style=False)

        total_files += 1
        total_waypoints += len(waypoints)
