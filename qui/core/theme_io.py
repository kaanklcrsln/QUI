"""Reading and writing ``.qui.json`` theme files and the bundled presets."""

from __future__ import annotations

import json
from pathlib import Path

from .theme_model import Theme

FILE_SUFFIX = ".qui.json"
PRESETS_DIR = Path(__file__).resolve().parents[1] / "presets"


class ThemeFileError(Exception):
    """A theme file could not be read or is not a valid QUI theme."""


def with_suffix(path: str | Path) -> Path:
    """*path* with ``.qui.json`` appended unless it already ends with it."""
    path = Path(path)
    return path if path.name.endswith(FILE_SUFFIX) else path.with_name(path.name + FILE_SUFFIX)


def save_theme(theme: Theme, path: str | Path) -> None:
    Path(path).write_text(json.dumps(theme.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_theme(path: str | Path) -> Theme:
    """Read a theme file; every failure is reported as ``ThemeFileError``."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ThemeFileError(f"Cannot read {path}: {error}") from error
    if not isinstance(data, dict):
        raise ThemeFileError(f"{path} is not a QUI theme")
    try:
        return Theme.from_dict(data)
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise ThemeFileError(f"{path} is not a valid QUI theme: {error}") from error


def list_presets() -> dict[str, Path]:
    """Bundled preset names (from the files) mapped to their paths, in file-name order."""
    return {load_theme(path).name: path for path in sorted(PRESETS_DIR.glob(f"*{FILE_SUFFIX}"))}
