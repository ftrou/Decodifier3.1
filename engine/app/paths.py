from functools import lru_cache
from pathlib import Path

from .config import get_settings


@lru_cache(maxsize=1)
def data_root() -> Path:
    """
    Resolve the root directory for all on-disk persistence.

    Priority:
    1. DECODIFIER_DATA_DIR env var (expanded with ~)
    2. Fallback to a global ~/.decodifier directory to keep repos clean
    """
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings.data_dir
