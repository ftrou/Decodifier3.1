import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List

# Shared ignore list for project registry, indexer, and patch APIs.
# These are hard exclusions that should never be indexed.
DEFAULT_IGNORE: List[str] = [
    ".git",
    ".decodifier",
    "node_modules",
    "dist",
    "venv",
    "__pycache__",
    ".pytest_cache",
]


def _default_data_dir() -> Path:
    override = os.getenv("DECODIFIER_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".decodifier"


@dataclass
class Settings:
    data_dir: Path = field(default_factory=_default_data_dir)
    project_registry_name: str = "projects.json"
    default_ignore: List[str] = field(default_factory=lambda: list(DEFAULT_IGNORE))
    embedding_model: str = os.getenv("DECODIFIER_EMBED_MODEL", "all-MiniLM-L6-v2")

    @property
    def project_registry_path(self) -> Path:
        return self.data_dir / self.project_registry_name


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
