"""The three-pane editor window: component tree | mockup | inspector."""

from __future__ import annotations

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QMainWindow, QSplitter, QWidget

from ..core.qss_generator import generate_qss
from ..core.selector_registry import COMPONENTS
from ..core.theme_applier import ui_theme_qss
from ..core.theme_model import Theme
from .component_tree import ComponentTree
from .inspector import Inspector
from .preview import PreviewPane

REFRESH_DELAY_MS = 40  # coalesce rapid edits (slider drags) into one restyle


class EditorWindow(QMainWindow):
    """Top-level editor window, parented to the QGIS main window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("QuiEditorWindow")
        self.setWindowTitle(self.tr("QUI - Quantum User Interfaces"))
        self.resize(1440, 880)

        # A new theme starts from the UI theme QGIS is currently running.
        self.theme = Theme(base_ui_theme=QgsApplication.themeName())
        self.selected: str | None = None
        self.tree = ComponentTree(parent=self)
        self.preview = PreviewPane(self)
        self.inspector = Inspector(self)
        self.inspector.global_panel.load(self.theme)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.preview)
        splitter.addWidget(self.inspector)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([230, 770, 440])  # inspector wide enough for five state tabs
        self.setCentralWidget(splitter)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(REFRESH_DELAY_MS)
        self._refresh_timer.timeout.connect(self.refresh_preview)

        self.tree.component_selected.connect(self.select_component)
        self.preview.picker.picked.connect(self.select_component)
        self.inspector.component_panel.changed.connect(self._component_edited)
        self.inspector.global_panel.changed.connect(self.set_global_value)
        self.inspector.global_panel.spread_radius_requested.connect(self.spread_radius)
        self.refresh_preview()

    # Selection ------------------------------------------------------------------------

    def select_component(self, component_id: str) -> None:
        """Select a component everywhere: tree, mockup highlight, inspector."""
        component = COMPONENTS[component_id]
        self.selected = component_id
        self.tree.select(component_id)
        visible = self.preview.highlight(component) > 0
        self.inspector.setCurrentIndex(0)
        self.inspector.component_panel.show_component(
            component, self.theme.component(component_id), self.theme.global_style.accent, visible
        )

    # Edits (single entry points; undo/redo wraps these) -------------------------------

    def set_state_value(self, component_id: str, state: str, field: str, value) -> None:
        """Set one property of one component state (``None`` = not set)."""
        setattr(self.theme.component(component_id).state(state), field, value)
        self.schedule_refresh()

    def set_global_value(self, field: str, value) -> None:
        """Set a theme-wide value; see ``GlobalPanel`` for the field names."""
        if field == "base_ui_theme":
            self.theme.base_ui_theme = value
        elif field == "font_family":
            self.theme.font.family = value
        elif field == "font_size":
            self.theme.font.point_size = value
        else:
            setattr(self.theme.global_style, field, value)
        if field == "accent":
            self.inspector.component_panel.set_accent(value)
        self.schedule_refresh()

    def spread_radius(self) -> None:
        """Copy the global radius into every component whose normal state has a background or border."""
        radius = self.theme.global_style.radius
        for component_id, style in self.theme.components.items():
            normal = style.states.get("normal")
            styled = normal is not None and (normal.background is not None or bool(normal.border_width))
            if styled and component_id in COMPONENTS and COMPONENTS[component_id].selectors:
                normal.border_radius = radius
        self.inspector.component_panel.reload()
        self.schedule_refresh()

    def _component_edited(self, state: str, field: str, value) -> None:
        if self.selected is not None:
            self.set_state_value(self.selected, state, field, value)

    # Preview --------------------------------------------------------------------------

    def schedule_refresh(self) -> None:
        self._refresh_timer.start()

    def preview_qss(self) -> str:
        """The stylesheet QGIS would get for the current theme, plus the main-window cascade."""
        qss = generate_qss(self.theme, ui_theme_qss(self.theme.base_ui_theme))
        # The mockups live in a graphics scene, outside the QGIS main window, so its own
        # stylesheet (e.g. "QGroupBox{ font-weight: 600; }") would not cascade into them.
        parent = self.parentWidget()
        if parent is not None and parent.styleSheet():
            qss += f"\n/* QGIS main-window stylesheet */\n{parent.styleSheet()}\n"
        return qss

    def preview_font(self) -> QFont:
        """The global font as QGIS would get it; unset parts inherit the application font."""
        font = QFont()
        if self.theme.font.family:
            font.setFamily(self.theme.font.family)
        if self.theme.font.point_size:
            font.setPointSizeF(self.theme.font.point_size)
        return font

    def refresh_preview(self) -> None:
        """Regenerate the QSS and font from the theme and show them on the mockups."""
        self._refresh_timer.stop()
        self.preview.apply_style(self.preview_qss(), self.preview_font())
        QTimer.singleShot(0, self.preview.refresh_highlight)  # after the new layout settles
