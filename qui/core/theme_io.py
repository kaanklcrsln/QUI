"""Reading and writing ``.qui.json`` theme files and the bundled presets."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .qss_generator import QUI_MARKER, generate_qss
from .theme_model import Theme

FILE_SUFFIX = ".qui.json"
PRESETS_DIR = Path(__file__).resolve().parents[1] / "presets"
_UNSAFE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class ThemeFileError(Exception):
    """A theme file could not be read or is not a valid QUI theme."""


def with_suffix(path: str | Path) -> Path:
    """*path* with ``.qui.json`` appended unless it already ends with it."""
    path = Path(path)
    return path if path.name.endswith(FILE_SUFFIX) else path.with_name(path.name + FILE_SUFFIX)


def save_theme(theme: Theme, path: str | Path) -> None:
    # LF on every platform so theme files diff and share cleanly (write_text(newline=) needs 3.10).
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(theme.to_dict(), indent=2, ensure_ascii=False) + "\n")


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


def qgis_theme_folder_name(name: str) -> str:
    """A folder name for *name* that is valid on every platform."""
    return _UNSAFE_NAME.sub("_", name).strip(" .") or "QUI theme"


def is_qui_export(folder: Path) -> bool:
    style = folder / "style.qss"
    return style.is_file() and QUI_MARKER in style.read_text(encoding="utf-8", errors="replace")


def export_qgis_theme(theme: Theme, folder: Path, base_theme_dir: str | Path | None = None) -> None:
    """Write *theme* as a regular QGIS UI theme folder (``style.qss`` + ``variables.qss``).

    The base theme's files (style, variables, palette.txt, icons) are copied *unresolved*
    and QUI's rules appended: QGIS itself substitutes ``@variables``/``@theme_path`` and
    scales ``em`` values on load, which must not happen twice. QUI's rules use px only.
    An existing folder is replaced only if QUI wrote it. The global font is not part of
    QGIS themes.
    """
    if folder.exists():
        if not is_qui_export(folder):
            raise ThemeFileError(f"{folder} exists and was not created by QUI; not overwriting it")
        shutil.rmtree(folder)
    if base_theme_dir:
        shutil.copytree(base_theme_dir, folder)
    else:
        folder.mkdir(parents=True)
    style = folder / "style.qss"
    base = style.read_text(encoding="utf-8") if style.is_file() else ""
    with open(style, "w", encoding="utf-8", newline="\n") as file:
        file.write(generate_qss(theme, base))
    variables = folder / "variables.qss"
    if not variables.is_file():
        with open(variables, "w", encoding="utf-8", newline="\n") as file:
            file.write("/* Exported by QUI: no variables. */\n")


def list_presets() -> dict[str, Path]:
    """Bundled preset names (from the files) mapped to their paths, in file-name order."""
    return {load_theme(path).name: path for path in sorted(PRESETS_DIR.glob(f"*{FILE_SUFFIX}"))}
