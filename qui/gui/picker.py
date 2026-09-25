"""Click-to-select on the mockups: find the component under the cursor, block real interaction."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from qgis.PyQt.QtCore import QEvent, QObject, QPoint, Qt, pyqtSignal
from qgis.PyQt.QtWidgets import QAbstractItemView, QDockWidget, QGroupBox, QMenu, QMenuBar, QTabBar, QWidget

from ..core.selector_registry import COMPONENTS, Component, SelectorPart, parse_selector, specificity

# Set this dynamic property to False on mockup parts QUI cannot style (map, message bar).
PICKABLE_PROPERTY = "quiPickable"

BLOCKED_EVENTS = {
    QEvent.Type.MouseButtonPress,
    QEvent.Type.MouseButtonRelease,
    QEvent.Type.MouseButtonDblClick,
    QEvent.Type.KeyPress,
    QEvent.Type.KeyRelease,
    QEvent.Type.Wheel,
    QEvent.Type.ContextMenu,
}


def widget_matches(parts: tuple[SelectorPart, ...], widget: QWidget) -> bool:
    """QSS-style right-to-left match of parsed selector *parts* against a live widget."""
    combinator, cls, name = parts[-1]
    if not widget.inherits(cls) or (name is not None and widget.objectName() != name):
        return False
    if len(parts) == 1:
        return True
    parent = widget.parentWidget()
    if combinator == ">":
        return parent is not None and widget_matches(parts[:-1], parent)
    while parent is not None:
        if widget_matches(parts[:-1], parent):
            return True
        parent = parent.parentWidget()
    return False


def component_matches(component: Component, widget: QWidget) -> bool:
    """True if any selector of *component* matches *widget* (sub-controls ignored)."""
    return any(widget_matches(parse_selector(s)[0], widget) for s in component.selectors)


def hits_sub_control(widget: QWidget, pos: QPoint, sub_control: str) -> bool:
    """True if *pos* (widget coordinates) lies on *sub_control* of *widget*."""
    if sub_control in ("item", "separator") and isinstance(widget, (QMenuBar, QMenu)):
        action = widget.actionAt(pos)
        return action is not None and action.isSeparator() == (sub_control == "separator")
    if sub_control == "item" and isinstance(widget, QAbstractItemView):
        return widget.indexAt(widget.viewport().mapFrom(widget, pos)).isValid()
    if sub_control == "tab" and isinstance(widget, QTabBar):
        return widget.tabAt(pos) >= 0
    if sub_control == "title" and isinstance(widget, QDockWidget):
        contents = widget.widget()
        return contents is not None and pos.y() < contents.geometry().top()
    if sub_control == "title" and isinstance(widget, QGroupBox):
        return pos.y() < widget.fontMetrics().height() + 4  # the label band at the top
    return False


def component_at(widget: QWidget, pos: QPoint, registry: Mapping[str, Component] = COMPONENTS) -> str | None:
    """Most specific component at *pos* in *widget*, searching up the parent chain.

    At each level, a component whose sub-control is hit beats plain matches; then
    higher specificity wins; ties go to the later registry entry (as in QSS).
    """
    while widget is not None:
        if widget.property(PICKABLE_PROPERTY) is False:
            return None
        best: tuple[tuple, str] | None = None
        for component in registry.values():
            for selector in component.selectors:
                parts, sub_control = parse_selector(selector)
                if not widget_matches(parts, widget):
                    continue
                if sub_control is not None and not hits_sub_control(widget, pos, sub_control):
                    continue
                key = (sub_control is not None, specificity(selector))
                if best is None or key >= best[0]:
                    best = (key, component.id)
        if best is not None:
            return best[1]
        pos = widget.mapToParent(pos)
        widget = widget.parentWidget()
    return None


def _event_pos(event) -> QPoint:
    return event.position().toPoint() if hasattr(event, "position") else event.pos()


class Picker(QObject):
    """Event filter on every mockup widget: left click picks, other input is swallowed."""

    picked = pyqtSignal(str)

    def __init__(self, roots: Iterable[QWidget], parent: QObject | None = None) -> None:
        super().__init__(parent)
        for root in roots:
            for widget in (root, *root.findChildren(QWidget)):
                widget.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            component_id = component_at(watched, _event_pos(event))
            if component_id is not None:
                self.picked.emit(component_id)
            return True
        return event.type() in BLOCKED_EVENTS
