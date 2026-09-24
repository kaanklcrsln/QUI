"""The three-pane editor window: component tree | mockup | inspector."""

from __future__ import annotations

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QLabel, QMainWindow, QSplitter, QWidget


class EditorWindow(QMainWindow):
    """Top-level editor window, parented to the QGIS main window.

    Parenting matters: QGIS's main-window stylesheet then cascades into the
    mockup exactly as it does into real QGIS dialogs (see docs/ARCHITECTURE.md).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("QuiEditorWindow")
        self.setWindowTitle(self.tr("QUI - Quantum User Interfaces"))
        self.resize(1280, 800)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._placeholder(self.tr("Component tree")))
        splitter.addWidget(self._placeholder(self.tr("QGIS mockup")))
        splitter.addWidget(self._placeholder(self.tr("Inspector")))
        splitter.setSizes([250, 780, 300])
        self.setCentralWidget(splitter)

    def _placeholder(self, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label
