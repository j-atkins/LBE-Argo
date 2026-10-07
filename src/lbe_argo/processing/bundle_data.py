"""Bundle the small files the analysis notebook needs into data/bundled/.

- {deployments,tracks,samples}.parquet: the slim simulation tables of every expedition
  (see lbe_argo.processing.slim_results), merged, with an `expedition` column;
- bathymetry.nc, model_mean_temp.nc: the ocean background fields (see
  lbe_argo.processing.ocean_background), computed from the raw ocean data.

Commit them, so the notebook can run without the raw data (e.g. in the cloud, where the files
are downloaded from GitHub). Re-run this after changing the simulations or the map region.

Usage:
    python -m lbe_argo.processing.bundle_data
"""

from lbe_argo.config import BUNDLE_DIR
from lbe_argo.processing.ocean_background import (
    BATHYMETRY_BUNDLE,
    MODEL_MEAN_BUNDLE,
    compute_bathymetry,
    compute_model_mean_temp,
)
from lbe_argo.processing.slim_results import build_bundle


def main() -> None:
    build_bundle()
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    for name, array, variable in [
        (BATHYMETRY_BUNDLE, compute_bathymetry(), "deptho"),
        (MODEL_MEAN_BUNDLE, compute_model_mean_temp(), "thetao"),
    ]:
        path = BUNDLE_DIR / name
        array.to_dataset(name=variable).to_netcdf(path)
        print(f"Wrote {path} ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
