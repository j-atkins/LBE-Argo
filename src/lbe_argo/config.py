from pathlib import Path

# ---
# Paths etc.


def find_project_root(current_path: Path) -> Path:
    """Find project root by searching upwards for expected files, e.g. pixi.toml."""
    for parent in current_path.parents:
        if (parent / "pixi.toml").exists() or (parent / "pyproject.toml").exists():
            return parent

    # fallback to relative depth if no marker found
    up_to_depth = 2
    print(
        f"Warning: Project root not found. Falling back to relative depth: {current_path.resolve().parents[up_to_depth]}"
    )
    return current_path.resolve().parents[up_to_depth]


PROJ_ROOT = find_project_root(Path(__file__).resolve())
DATA_DIR = PROJ_ROOT / "data"
EXPEDITIONS_DIR = DATA_DIR / "expeditions"
OCEAN_DATA_DIR = DATA_DIR / "ocean"

PHYS_DATA_DIR = OCEAN_DATA_DIR / "phys"

BATHYMETRY_FPATH = (
    OCEAN_DATA_DIR
    / "bathymetry"
    / "cmems_mod_glo_phy_anfc_0.083deg_static_bathymetry.nc"
)

# ---
# Simulation parameters for Argo floats in the Lofoten Basin

ARGO_CONFIG = {
    "cycle_days": 10.0,
    "drift_days": 9.0,
    "drift_depth_meter": -1000.0,  # Standard 1000m parking depth
    "lifetime_days": 365.0,  # 1-year lifetime
    "max_depth_meter": -2000.0,  # 2000m profiling depth
    "min_depth_meter": 0.0,
    "sensors": ["TEMPERATURE", "SALINITY"],
    "stationkeeping_time_minutes": 20.0,
    "vertical_speed_meter_per_second": -0.1,
}
