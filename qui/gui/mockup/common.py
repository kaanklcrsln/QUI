"""Small helpers shared by the mockups."""

from __future__ import annotations

from qgis.core import QgsApplication
from qgis.PyQt.QtGui import QIcon


def icon(name: str) -> QIcon:
    """QGIS theme icon by base name, e.g. ``icon("mActionPan")`` or ``icon("propertyicons/general")``."""
    return QgsApplication.getThemeIcon(f"/{name}.svg")


def add_action(
    target, icon_name: str | None, text: str, *, checked: bool | None = None, enabled: bool = True
):
    """Add an action to a menu or toolbar; ``checked`` makes it checkable."""
    action = target.addAction(icon(icon_name), text) if icon_name else target.addAction(text)
    if checked is not None:
        action.setCheckable(True)
        action.setChecked(checked)
    action.setEnabled(enabled)
    return action
