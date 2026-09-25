"""Left pane: the component hierarchy from the selector registry."""

from __future__ import annotations

from collections.abc import Mapping

from qgis.PyQt.QtCore import QCoreApplication, Qt, pyqtSignal
from qgis.PyQt.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget

from ..core.selector_registry import COMPONENTS, Component

ID_ROLE = Qt.ItemDataRole.UserRole


class ComponentTree(QTreeWidget):
    """Every registry component; grouping nodes (no selectors) are not selectable."""

    component_selected = pyqtSignal(str)

    def __init__(self, registry: Mapping[str, Component] = COMPONENTS, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)
        self._items: dict[str, QTreeWidgetItem] = {}
        for component in registry.values():
            parent_item = self._items.get(component.parent) if component.parent else None
            item = QTreeWidgetItem(parent_item if parent_item is not None else self)
            item.setText(0, QCoreApplication.translate("QuiComponents", component.label))
            item.setData(0, ID_ROLE, component.id)
            if component.selectors:
                item.setToolTip(0, "\n".join(component.selectors))
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._items[component.id] = item
        self.expandToDepth(0)
        self.itemSelectionChanged.connect(self._emit_selection)

    def _emit_selection(self) -> None:
        items = self.selectedItems()
        if items:
            self.component_selected.emit(items[0].data(0, ID_ROLE))

    def select(self, component_id: str) -> None:
        """Select *component_id* without emitting ``component_selected``."""
        item = self._items.get(component_id)
        if item is None:
            return
        self.blockSignals(True)
        self.setCurrentItem(item)
        self.blockSignals(False)
        self.scrollToItem(item)
