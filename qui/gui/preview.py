"""Zoomable preview hosting the mockups; only the mockups receive the preview stylesheet."""

from __future__ import annotations

from qgis.PyQt.QtCore import QEvent, Qt
from qgis.PyQt.QtGui import QColor, QPainter, QTransform
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QSizePolicy,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .mockup import MockMainWindow, MockOptionsDialog
from .mockup.common import icon

LIGHT_BACKGROUND, DARK_BACKGROUND = "#e9e9ed", "#1e1f22"


class PreviewPane(QWidget):
    """Mockups in a QGraphicsScene (for zoom) plus the view/zoom/background controls."""

    MIN_ZOOM, MAX_ZOOM, ZOOM_STEP = 0.25, 3.0, 1.2

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mockups: dict[str, QWidget] = {"main_window": MockMainWindow(), "dialog": MockOptionsDialog()}
        self.scene = QGraphicsScene(self)
        self.proxies = {key: self.scene.addWidget(widget) for key, widget in self.mockups.items()}
        self.view = QGraphicsView(self.scene, self)
        self.view.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.zoom = 1.0
        self._auto_fit = True  # keep fitting on resize until the user zooms manually
        self.view.viewport().installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toolbar())
        layout.addWidget(self.view, 1)
        self.set_dark_background(False)
        self.show_view("main_window")

    def _toolbar(self) -> QToolBar:
        bar = QToolBar(self)
        self.view_combo = QComboBox(bar)
        self.view_combo.addItem(self.tr("QGIS main window"), "main_window")
        self.view_combo.addItem(self.tr("Options dialog"), "dialog")
        self.view_combo.currentIndexChanged.connect(lambda: self.show_view(self.view_combo.currentData()))
        bar.addWidget(self.view_combo)
        bar.addSeparator()
        bar.addAction(icon("mActionZoomOut"), self.tr("Zoom out")).triggered.connect(
            lambda: self.set_zoom(self.zoom / self.ZOOM_STEP)
        )
        self.zoom_label = QLabel(bar)
        self.zoom_label.setMinimumWidth(44)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar.addWidget(self.zoom_label)
        bar.addAction(icon("mActionZoomIn"), self.tr("Zoom in")).triggered.connect(
            lambda: self.set_zoom(self.zoom * self.ZOOM_STEP)
        )
        bar.addAction(icon("mActionZoomFullExtent"), self.tr("Fit to view")).triggered.connect(self.fit)
        spacer = QWidget(bar)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bar.addWidget(spacer)
        dark = bar.addAction(self.tr("Dark background"))
        dark.setCheckable(True)
        dark.toggled.connect(self.set_dark_background)
        return bar

    def set_stylesheet(self, qss: str) -> None:
        """Apply *qss* to every mockup (never to the editor's own widgets)."""
        for widget in self.mockups.values():
            widget.setStyleSheet(qss)

    def show_view(self, key: str) -> None:
        """Show one mockup ("main_window" or "dialog") and fit it."""
        for name, proxy in self.proxies.items():
            proxy.setVisible(name == key)
        self.scene.setSceneRect(self.proxies[key].sceneBoundingRect())
        self._auto_fit = True
        self.fit()

    def set_zoom(self, factor: float, *, manual: bool = True) -> None:
        self.zoom = min(max(factor, self.MIN_ZOOM), self.MAX_ZOOM)
        self._auto_fit = self._auto_fit and not manual
        self.view.setTransform(QTransform.fromScale(self.zoom, self.zoom))
        self.zoom_label.setText(f"{round(self.zoom * 100)}%")

    def fit(self) -> None:
        """Zoom so the current mockup fits the view (never above 100%)."""
        rect = self.scene.sceneRect()
        viewport = self.view.viewport().size()
        if rect.isEmpty() or viewport.isEmpty():
            return
        factor = min((viewport.width() - 16) / rect.width(), (viewport.height() - 16) / rect.height(), 1.0)
        self.set_zoom(factor, manual=False)

    def set_dark_background(self, dark: bool) -> None:
        self.view.setBackgroundBrush(QColor(DARK_BACKGROUND if dark else LIGHT_BACKGROUND))

    def eventFilter(self, watched, event) -> bool:
        # Fit on the viewport's own resize: the pane's resizeEvent fires before layout.
        if watched is self.view.viewport() and event.type() == QEvent.Type.Resize and self._auto_fit:
            self.fit()
        return super().eventFilter(watched, event)
