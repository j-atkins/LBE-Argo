"""Access to the files bundled in `data/bundled/` (see lbe_argo.processing.bundle_data)."""

import tempfile
import urllib.request
from pathlib import Path

from lbe_argo.config import BUNDLE_DIR, BUNDLE_URL

CACHE_DIR = Path(tempfile.gettempdir()) / "lbe_argo_bundle"


def bundled_file(name: str) -> Path:
    """Path of a bundled file: from the repo if it's there, otherwise downloaded from GitHub."""
    local = BUNDLE_DIR / name
    if local.exists():
        return local
    cached = CACHE_DIR / name
    if not cached.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        partial = cached.with_name(cached.name + ".part")
        urllib.request.urlretrieve(f"{BUNDLE_URL}/{name}", partial)
        partial.rename(cached)
    return cached


def has_local_bundled_file(name: str) -> bool:
    return (BUNDLE_DIR / name).exists()
