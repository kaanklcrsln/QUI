"""Everything that reads or changes the live QGIS styling."""

from __future__ import annotations

import json
from pathlib import Path

from qgis.core import Qgis, QgsApplication, QgsSettings
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QApplication

from .qss_generator import generate_qss, resolve_ui_theme
from .theme_model import Theme

# QUI's only settings; it never writes QGIS's own UI/UITheme or app/font* keys.
KEPT_THEME_KEY = "qui/keptTheme"
AUTO_APPLY_KEY = "qui/autoApplyOnStartup"


BUNDLED_THEMES_DIR = Path(__file__).resolve().parents[1] / "themes"


def bundled_theme_info() -> list[dict]:
    """Third-party themes shipped with QUI (imported from pinned upstream commits), with attribution."""
    manifest = BUNDLED_THEMES_DIR / "themes.json"
    return json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else []


def ui_themes() -> dict[str, str]:
    """Every usable base theme, name -> folder: QGIS's own themes, then QUI's bundled ones."""
    themes = dict(QgsApplication.uiThemes())
    for info in bundled_theme_info():
        themes.setdefault(info["name"], str(BUNDLED_THEMES_DIR / info["id"]))
    return themes


def ui_theme_qss(name: str) -> str:
    """Resolved QSS of the UI theme *name*; ``''`` for "default" or unknown.

    Uses the running QGIS's own theme path and UI scale, so for QGIS's themes the result
    is byte-identical to what ``QgsApplication.setUITheme(name)`` applies.
    """
    path = ui_themes().get(name, "")
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


def theme_font(theme: Theme, base: QFont) -> QFont:
    """*base* with the theme's global family/size applied (unset parts keep *base*)."""
    font = QFont(base)
    if theme.font.family:
        font.setFamily(theme.font.family)
    if theme.font.point_size:
        font.setPointSizeF(theme.font.point_size)
    return font


class ThemeApplier:
    """Applies themes to the running application and restores its exact original look.

    Only the application stylesheet and the application font are changed, in memory.
    The original pair is captured on the first ``apply`` and survives re-applies.
    """

    def __init__(self, app: QApplication | None = None) -> None:
        self._app = app or QApplication.instance()
        self._original: tuple[str, QFont] | None = None
        self._applied: tuple[str, QFont] | None = None
        self._pending: dict | None = None  # applied, awaiting keep()/revert()
        self._kept: dict | None = None

    @property
    def is_applied(self) -> bool:
        return self._applied is not None

    @property
    def original_font(self) -> QFont:
        return QFont(self._original[1] if self._original else self._app.font())

    def apply(self, theme: Theme) -> None:
        app = self._app
        if self._original is None:
            self._original = (app.styleSheet(), QFont(app.font()))
        qss = generate_qss(theme, ui_theme_qss(theme.base_ui_theme))
        font = theme_font(theme, self._original[1])
        # Stylesheet polishing pins each widget's font, so a font change needs a re-polish:
        # set the font first, and if the sheet is unchanged, drop it for a moment.
        if app.styleSheet() == qss and app.font() != font:
            app.setStyleSheet("")
        app.setFont(font)
        app.setStyleSheet(qss)
        self._applied = (app.styleSheet(), QFont(app.font()))
        self._pending = theme.to_dict()

    def keep(self) -> None:
        """Confirm the last applied theme; it is re-applied when QGIS starts."""
        self._kept = self._pending
        QgsSettings().setValue(KEPT_THEME_KEY, json.dumps(self._kept))

    def revert(self) -> None:
        """Undo the last apply: back to the previously kept theme, else the original look."""
        if self._kept is not None:
            self.apply(Theme.from_dict(self._kept))
            self._pending = self._kept
        else:
            self.restore()

    def restore(self, forget: bool = True) -> bool:
        """Put the original stylesheet and font back; False if nothing was applied.

        A part that something else changed after QUI (e.g. the user picked another UI
        theme in Options) is left alone. ``forget=False`` keeps the kept theme stored
        for the next start (used on plugin unload, which also happens when QGIS exits).
        """
        if forget:
            self._kept = None
            QgsSettings().remove(KEPT_THEME_KEY)
        if self._applied is None:
            return False
        app = self._app
        (original_qss, original_font), (applied_qss, applied_font) = self._original, self._applied
        if app.font() == applied_font:
            app.setFont(original_font)
        if app.styleSheet() == applied_qss:
            app.setStyleSheet(original_qss)
        self._original = self._applied = self._pending = None
        return True


def stored_theme() -> Theme | None:
    """The theme kept last time, if auto-apply is on and the stored value is valid."""
    settings = QgsSettings()
    if not settings.value(AUTO_APPLY_KEY, True, type=bool):
        return None
    raw = settings.value(KEPT_THEME_KEY, "")
    if not raw:
        return None
    try:
        return Theme.from_dict(json.loads(raw))
    except (ValueError, TypeError, KeyError):
        return None
