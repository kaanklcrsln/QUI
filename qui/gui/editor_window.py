"""The three-pane editor window: component tree | mockup | inspector."""

from __future__ import annotations

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QLabel, QMainWindow, QSplitter, QWidget

from ..core.qss_generator import generate_qss
from ..core.selector_registry import COMPONENTS
from ..core.theme_applier import ui_theme_qss
from ..core.theme_model import Theme
from .component_tree import ComponentTree
from .preview import PreviewPane


class EditorWindow(QMainWindow):
    """Top-level editor window, parented to the QGIS main window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("QuiEditorWindow")
        self.setWindowTitle(self.tr("QUI - Quantum User Interfaces"))
        self.resize(1400, 860)

        # A new theme starts from the UI theme QGIS is currently running.
        self.theme = Theme(base_ui_theme=QgsApplication.themeName())
        self.selected: str | None = None
        self.tree = ComponentTree(parent=self)
        self.preview = PreviewPane(self)
        self.inspector = QLabel(self.tr("Click a part of the mockup or pick a component on the left."), self)
        self.inspector.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inspector.setWordWrap(True)
        self.inspector.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.preview)
        splitter.addWidget(self.inspector)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([250, 850, 300])
        self.setCentralWidget(splitter)

        self.tree.component_selected.connect(self.select_component)
        self.preview.picker.picked.connect(self.select_component)
        self.refresh_preview()

    def select_component(self, component_id: str) -> None:
        """Select a component everywhere: tree, mockup highlight, inspector."""
        component = COMPONENTS[component_id]
        self.selected = component_id
        self.tree.select(component_id)
        shown = self.preview.highlight(component)
        label = QCoreApplication.translate("QuiComponents", component.label)
        note = "" if shown else "<br><i>" + self.tr("Not visible in the mockup.") + "</i>"
        selectors = "<br>".join(component.selectors)
        self.inspector.setText(f"<b>{label}</b><br><code>{selectors}</code>{note}")

    def preview_qss(self) -> str:
        """The stylesheet QGIS would get for the current theme, plus the main-window cascade."""
        qss = generate_qss(self.theme, ui_theme_qss(self.theme.base_ui_theme))
        # The mockups live in a graphics scene, outside the QGIS main window, so its own
        # stylesheet (e.g. "QGroupBox{ font-weight: 600; }") would not cascade into them.
        parent = self.parentWidget()
        if parent is not None and parent.styleSheet():
            qss += f"\n/* QGIS main-window stylesheet */\n{parent.styleSheet()}\n"
        return qss

    def refresh_preview(self) -> None:
        """Regenerate the QSS from the theme and show it on the mockups."""
        self.preview.set_stylesheet(self.preview_qss())
