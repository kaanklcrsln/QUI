"""Right pane: component and global style editors."""

from __future__ import annotations

from qgis.PyQt.QtWidgets import QScrollArea, QTabWidget, QWidget

from .component_panel import ComponentPanel
from .global_panel import GlobalPanel


def _scrollable(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area


class Inspector(QTabWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.component_panel = ComponentPanel()
        self.global_panel = GlobalPanel()
        self.addTab(_scrollable(self.component_panel), self.tr("Component"))
        self.addTab(_scrollable(self.global_panel), self.tr("Global"))


__all__ = ["ComponentPanel", "GlobalPanel", "Inspector"]
