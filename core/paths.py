import sys
from pathlib import Path


def _frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_app_dir() -> Path:
    """Writable directory next to the executable (config, database)."""
    if _frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def get_assets_dir() -> Path:
    """Read-only assets bundled with the app (fonts, icons)."""
    if _frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent
