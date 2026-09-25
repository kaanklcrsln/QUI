"""Logical UI components and the QSS selectors that target them.

Each selector must match both the QUI mockup and real QGIS; private QGIS classes are
addressed through a public base class plus objectName (``QMainWindow#QgisApp``).
tests/test_selector_registry.py checks every selector against tools/dumps/*.json.

Registry order is both the component-tree order and the QSS rule order, so generic
components come before the specific ones that refine them.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cache

DEFAULT_PSEUDO: Mapping[str, str] = {
    "normal": "",
    "hover": ":hover",
    "pressed": ":pressed",
    "selected": ":selected",
    "disabled": ":disabled",
    "checked": ":checked",
}

BOX = ("normal",)
BUTTON = ("normal", "hover", "pressed", "checked", "disabled")
ITEM = ("normal", "hover", "selected", "disabled")


@dataclass(frozen=True)
class Component:
    """One selectable UI part. No selectors means a grouping node in the tree."""

    id: str
    label: str  # English; shown via QCoreApplication.translate("QuiComponents", label)
    selectors: tuple[str, ...] = ()
    states: tuple[str, ...] = BOX
    parent: str | None = None
    pseudo_overrides: Mapping[str, str] = field(default_factory=dict)

    def pseudo(self, state: str) -> str:
        """QSS pseudo-state suffix used for *state* on this component."""
        return self.pseudo_overrides.get(state, DEFAULT_PSEUDO[state])


SelectorPart = tuple[str, str, "str | None"]  # (combinator " " or ">", class, objectName)


@cache
def parse_selector(selector: str) -> tuple[tuple[SelectorPart, ...], str | None]:
    """Split one selector into compound parts and its sub-control; pseudo-states are dropped.

    ``'A#x > B C::item:hover'`` -> ``(((' ', 'A', 'x'), ('>', 'B', None), (' ', 'C', None)), 'item')``
    """
    sub_control = re.search(r"::([\w-]+)", selector)
    bare = re.sub(r"::?[\w-]+", "", selector)
    parts, combinator = [], " "
    for token in re.findall(r">|[^\s>]+", bare):
        if token == ">":
            combinator = ">"
            continue
        cls, _, name = token.partition("#")
        parts.append((combinator, cls, name or None))
        combinator = " "
    return tuple(parts), sub_control.group(1) if sub_control else None


def specificity(selector: str) -> tuple[int, int]:
    """Simplified QSS specificity: (objectName count, type + sub-control count)."""
    parts, sub_control = parse_selector(selector)
    return sum(name is not None for _, _, name in parts), len(parts) + (sub_control is not None)


def _both_browsers(suffix: str) -> tuple[str, ...]:
    return tuple(f"QDockWidget#{name}{suffix}" for name in ("Browser", "Browser2"))


_COMPONENTS = (
    # Common controls (dialogs, panels, everywhere)
    Component("controls", "Common controls"),
    Component("button", "Push buttons", ("QPushButton",), BUTTON, "controls"),
    # QSS text color does not inherit, so dark themes must color plain text explicitly.
    Component("label", "Labels, check boxes and radio buttons", ("QLabel", "QCheckBox", "QRadioButton"),
              ("normal", "disabled"), "controls"),
    Component("input", "Text and number fields", ("QLineEdit", "QAbstractSpinBox"),
              ("normal", "hover", "disabled"), "controls"),
    Component("combo", "Drop-down lists", ("QComboBox",), ("normal", "hover", "disabled"), "controls"),
    Component("tab", "Tabs", ("QTabBar::tab",), ("normal", "hover", "selected", "disabled"), "controls"),
    Component("tab_pane", "Tab page frame", ("QTabWidget::pane",), BOX, "tab"),
    # QScrollArea.setWidget() turns on palette fill for the contents, so it needs its own rule.
    Component("scroll_area", "Scroll areas",
              ("QScrollArea", "QScrollArea > QWidget#qt_scrollarea_viewport > QWidget"), BOX, "controls"),
    Component("group_box", "Group boxes", ("QGroupBox",), ("normal", "disabled"), "controls"),
    Component("group_box.title", "Group box titles", ("QGroupBox::title",), ("normal", "disabled"),
              "group_box"),
    Component("item_view", "Lists, trees and tables", ("QAbstractItemView",), ("normal", "disabled"),
              "controls"),
    Component("item_view.item", "List items", ("QAbstractItemView::item",), ITEM, "item_view"),
    Component("item_view.header", "Table headers", ("QHeaderView::section", "QTableCornerButton::section"),
              ("normal", "hover"), "item_view"),
    Component("tooltip", "Tooltips", ("QToolTip",), BOX, "controls"),
    # Main window
    Component("main_window", "Main window", ("QMainWindow#QgisApp",)),
    Component("main_window.separator", "Panel separators", ("QMainWindow#QgisApp::separator",),
              ("normal", "hover"), "main_window"),
    Component("menubar", "Menu bar", ("QMenuBar#menubar",), BOX, "main_window"),
    Component("menubar.item", "Menu bar items", ("QMenuBar#menubar::item",),
              ("normal", "hover", "pressed", "disabled"), "menubar", {"hover": ":selected"}),
    Component("menu", "Menus", ("QMenu",), BOX, "main_window"),
    Component("menu.item", "Menu items", ("QMenu::item",), ("normal", "hover", "disabled"), "menu",
              {"hover": ":selected"}),
    Component("menu.separator", "Menu separators", ("QMenu::separator",), BOX, "menu"),
    Component("toolbar", "Toolbars", ("QMainWindow#QgisApp > QToolBar",), BOX, "main_window"),
    Component("toolbar.button", "Toolbar buttons", ("QMainWindow#QgisApp > QToolBar QToolButton",),
              BUTTON, "toolbar"),
    Component("dock", "Panels", ("QDockWidget",), BOX, "main_window"),
    Component("dock.title", "Panel titles", ("QDockWidget::title",), BOX, "dock"),
    Component("layers_panel", "Layers panel", ("QDockWidget#Layers",), BOX, "dock"),
    Component("layers_panel.toolbar", "Layers panel toolbar", ("QDockWidget#Layers QToolBar",),
              BOX, "layers_panel"),
    Component("layers_panel.tree", "Layer tree", ("QgsLayerTreeView#theLayerTreeView",), BOX,
              "layers_panel"),
    Component("layers_panel.tree.item", "Layer tree items", ("QgsLayerTreeView#theLayerTreeView::item",),
              ITEM, "layers_panel.tree"),
    Component("browser_panel", "Browser panel", _both_browsers(""), BOX, "dock"),
    Component("browser_panel.toolbar", "Browser panel toolbar", _both_browsers(" QToolBar#mBrowserToolbar"),
              BOX, "browser_panel"),
    Component("browser_panel.tree", "Browser tree", _both_browsers(" QTreeView"), BOX, "browser_panel"),
    Component("browser_panel.tree.item", "Browser tree items", _both_browsers(" QTreeView::item"), ITEM,
              "browser_panel.tree"),
    Component("statusbar", "Status bar", ("QStatusBar#statusbar",), BOX, "main_window"),
    Component("statusbar.text", "Status bar text", ("QStatusBar#statusbar QLabel",), BOX, "statusbar"),
    # Dialogs (Options, Layer Properties, Plugin Manager share this skeleton)
    Component("dialog", "Dialogs", ("QDialog",)),
    Component("dialog.page_list", "Dialog page list", ("QListWidget#mOptionsListWidget",),
              ("normal", "disabled"), "dialog"),
    Component("dialog.page_list.item", "Dialog page list items", ("QListWidget#mOptionsListWidget::item",),
              ITEM, "dialog.page_list"),
)  # fmt: skip

COMPONENTS: Mapping[str, Component] = {c.id: c for c in _COMPONENTS}
