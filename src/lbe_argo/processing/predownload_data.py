import pandas as pd
import copernicusmarine
from lbe_argo.config import BATHYMETRY_FPATH, PHYS_DATA_DIR

## Overwrite data if already exists? Set to True to force re-download, False to skip existing files.
OVERWRITE_EXISTING = False

### BATHYMETRY FILE (GLOBAL)
DATASET_ID_BATHYMETRY = "cmems_mod_glo_phy_anfc_0.083deg_static"


if not BATHYMETRY_FPATH.exists() or OVERWRITE_EXISTING:
    copernicusmarine.subset(
        dataset_id=DATASET_ID_BATHYMETRY,
        dataset_part="bathy",
        variables=["deptho"],
        minimum_longitude=-180,
        maximum_longitude=179.91668701171875,
        minimum_latitude=-80,
        maximum_latitude=90,
        minimum_depth=0.49402499198913574,
        maximum_depth=0.49402499198913574,
        output_filename=BATHYMETRY_FPATH,
    )

### PHYSICAL DAILY FILES

DATASET_ID = "cmems_mod_glo_phy_my_0.083deg_P1D-m"

dates = pd.date_range(start="1993-01-01", end="2024-12-31", freq="D")

for dt in dates:
    date_str = dt.strftime("%Y_%m_%d")
    iso_time = dt.strftime("%Y-%m-%dT00:00:00")

    filename = PHYS_DATA_DIR / f"{DATASET_ID}_global_fulldepth_{date_str}.nc"

    if filename.exists() and not OVERWRITE_EXISTING:
        print(f"File {filename} already exists, skipping...")
        continue

    copernicusmarine.subset(
        dataset_id=DATASET_ID,
        variables=["uo", "vo", "thetao", "so"],
        minimum_longitude=-5.0,
        maximum_longitude=20.0,
        minimum_latitude=64.0,
        maximum_latitude=78.0,
        start_datetime=iso_time,
        end_datetime=iso_time,
        minimum_depth=0.0,
        maximum_depth=2010.0,
        coordinates_selection_method="outside",
        output_filename=filename,
    )
