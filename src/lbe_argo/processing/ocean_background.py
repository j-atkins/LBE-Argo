"""The ocean background fields used by the analysis notebook: bathymetry, and the model's
time-mean temperature at the depth slices of the 3D picture.

Both are tiny compared with the raw ocean data (hundreds of GB), so they are bundled into
`data/bundled/` (see lbe_argo.processing.bundle_data) and committed, which lets the notebook
run without the raw data, e.g. in the cloud. With the raw data on disk and no bundle, they
are computed from the raw data instead.
"""

import math

import xarray as xr

from lbe_argo.bundled import bundled_file, has_local_bundled_file
from lbe_argo.config import BATHYMETRY_FPATH, PHYS_DATA_DIR

BATHYMETRY_BUNDLE = "bathymetry.nc"
MODEL_MEAN_BUNDLE = "model_mean_temp.nc"

MAP_EXTENT = [
    -5,
    20,
    64,
    78,
]  # lon_min, lon_max, lat_min, lat_max of the ocean data used
COMPOSITE_DEPTHS_M = [200, 500, 800, 1200, 1600]  # depth slices of the 3D picture
MODEL_MEAN_MAX_FILES = 120  # daily files averaged for the model climatology


def _region() -> dict:
    lon_min, lon_max, lat_min, lat_max = MAP_EXTENT
    return dict(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))


def _raw_model_files() -> list:
    return sorted(PHYS_DATA_DIR.glob("*.nc"))


def model_data_available() -> bool:
    """Whether the model's temperature is available (the bundle can always be downloaded)."""
    return True


def compute_bathymetry() -> xr.DataArray:
    """Sea floor depth (m) in the map region from the raw data, NaN on land."""
    with xr.open_dataset(BATHYMETRY_FPATH) as ds:
        return ds.deptho.sel(**_region()).load()


def compute_model_mean_temp() -> xr.DataArray:
    """Time-mean model temperature at COMPOSITE_DEPTHS_M from the raw daily files."""
    files = _raw_model_files()
    # an evenly spaced subset of the daily files is plenty for the climatology
    subset = files[:: max(1, math.ceil(len(files) / MODEL_MEAN_MAX_FILES))]
    with xr.open_mfdataset(
        subset,
        combine="by_coords",
        data_vars="minimal",
        coords="minimal",
        compat="override",
    ) as ds:
        # the model's own depth levels are irregular (186m, 541m...), so keep the levels
        # around the ones we want and interpolate onto round depths
        return (
            ds.thetao.sel(depth=slice(0, max(COMPOSITE_DEPTHS_M) + 200))
            .mean("time")
            .sel(**_region())
            .load()
            .interp(depth=COMPOSITE_DEPTHS_M)
        )


def load_bathymetry() -> xr.DataArray:
    """Sea floor depth (m) in the map region, NaN on land."""
    if not has_local_bundled_file(BATHYMETRY_BUNDLE) and BATHYMETRY_FPATH.exists():
        return compute_bathymetry()
    with xr.open_dataset(bundled_file(BATHYMETRY_BUNDLE)) as ds:
        return ds.deptho.load()


def load_model_mean_temp() -> xr.DataArray:
    """Time-mean model temperature at COMPOSITE_DEPTHS_M."""
    if not has_local_bundled_file(MODEL_MEAN_BUNDLE) and _raw_model_files():
        return compute_model_mean_temp()
    with xr.open_dataset(bundled_file(MODEL_MEAN_BUNDLE)) as ds:
        return ds.thetao.load()
