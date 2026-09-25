"""The three-pane editor window: component tree | mockup | inspector."""

from __future__ import annotations

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QLabel, QMainWindow, QSplitter, QWidget

from ..core.qss_generator import generate_qss
from ..core.theme_applier import ui_theme_qss
from ..core.theme_model import Theme
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
        self.preview = PreviewPane(self)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._placeholder(self.tr("Component tree")))
        splitter.addWidget(self.preview)
        splitter.addWidget(self._placeholder(self.tr("Inspector")))
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([250, 850, 300])
        self.setCentralWidget(splitter)
        self.refresh_preview()

    def _placeholder(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

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
