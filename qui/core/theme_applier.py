"""Everything that reads or changes the live QGIS styling."""

from __future__ import annotations

from pathlib import Path

from qgis.core import Qgis, QgsApplication

from .qss_generator import resolve_ui_theme


def ui_theme_qss(name: str) -> str:
    """Resolved QSS of the installed QGIS UI theme *name*; ``''`` for "default" or unknown.

    Uses the running QGIS's own theme path and UI scale, so the result is byte-identical
    to what ``QgsApplication.setUITheme(name)`` applies.
    """
    path = QgsApplication.uiThemes().get(name, "")
    style = Path(path, "style.qss") if path else None
    if style is None or not style.is_file():
        return ""
    variables = Path(path, "variables.qss")
    return resolve_ui_theme(
        style.read_text(encoding="utf-8"),
        variables.read_text(encoding="utf-8") if variables.is_file() else "",
        path,
        Qgis.UI_SCALE_FACTOR,
    )
