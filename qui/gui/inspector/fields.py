"""Nullable property editors: a checkbox (set / not set) plus an editor widget."""

from __future__ import annotations

from qgis.gui import QgsColorButton
from qgis.PyQt.QtCore import QObject, Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QSlider,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...core.theme_model import ACCENT_TOKEN, Gradient, GradientStop, Padding, parse_color


def to_qcolor(value: str) -> QColor:
    return QColor(*parse_color(value))


def to_hex(color: QColor) -> str:
    """``#rrggbb``, or ``#rrggbbaa`` when not fully opaque."""
    text = f"#{color.red():02x}{color.green():02x}{color.blue():02x}"
    return text if color.alpha() == 255 else f"{text}{color.alpha():02x}"


def row_widget(*widgets: QWidget) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    for widget in widgets:
        layout.addWidget(widget)
    return container


class ColorEditor(QWidget):
    """QGIS color button (with opacity) plus an optional "link to accent" toggle."""

    changed = pyqtSignal()

    def __init__(
        self, default: str = "#808080", allow_accent: bool = True, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._accent = "#3b82f6"
        self.button = QgsColorButton(self)
        self.button.setAllowOpacity(True)
        self.button.setMinimumWidth(90)
        self.button.setColor(to_qcolor(default))
        self.button.colorChanged.connect(self.changed)
        self.accent_toggle = QToolButton(self)
        self.accent_toggle.setText("@")
        self.accent_toggle.setCheckable(True)
        self.accent_toggle.setToolTip(self.tr("Use the theme accent color"))
        self.accent_toggle.setVisible(allow_accent)
        self.accent_toggle.toggled.connect(self._accent_toggled)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.button, 1)
        layout.addWidget(self.accent_toggle)

    def value(self) -> str:
        return ACCENT_TOKEN if self.accent_toggle.isChecked() else to_hex(self.button.color())

    def set_value(self, value: str) -> None:
        """Show *value* without emitting ``changed``."""
        self.blockSignals(True)
        linked = value == ACCENT_TOKEN
        self.accent_toggle.setChecked(linked)
        self._show_color(self._accent if linked else value)
        self.button.setEnabled(not linked)
        self.blockSignals(False)

    def set_accent(self, accent: str) -> None:
        self._accent = accent
        if self.accent_toggle.isChecked():
            self._show_color(accent)

    def _show_color(self, value: str) -> None:
        self.button.blockSignals(True)
        self.button.setColor(to_qcolor(value))
        self.button.blockSignals(False)

    def _accent_toggled(self, linked: bool) -> None:
        self.button.setEnabled(not linked)
        if linked:
            self._show_color(self._accent)
        self.changed.emit()


class Field(QObject):
    """A nullable style property. Subclasses build an editor and call ``_attach``;
    the panel adds ``check`` and ``editor`` as one form row."""

    changed = pyqtSignal(object)  # the new value, or None when unchecked

    def __init__(self, label: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.check = QCheckBox(label)
        self.editor: QWidget | None = None
        self._loading = False

    def _attach(self, editor: QWidget) -> None:
        self.editor = editor
        editor.setEnabled(False)
        self.check.toggled.connect(self._toggled)

    def value(self):
        return self.read() if self.check.isChecked() else None

    def set_value(self, value) -> None:
        """Show *value* (None = not set) without emitting ``changed``."""
        self._loading = True
        try:
            self.check.setChecked(value is not None)
            self.editor.setEnabled(value is not None)
            if value is not None:
                self.write(value)
        finally:
            self._loading = False

    def emit_change(self) -> None:
        if not self._loading:
            self.changed.emit(self.value())

    def _toggled(self, checked: bool) -> None:
        self.editor.setEnabled(checked)
        self.emit_change()

    def set_accent(self, accent: str) -> None:
        """Fields with color editors show *accent* for accent-linked colors."""

    def read(self):
        raise NotImplementedError

    def write(self, value) -> None:
        raise NotImplementedError


class ColorField(Field):
    def __init__(self, label: str, default: str = "#808080", parent: QObject | None = None) -> None:
        super().__init__(label, parent)
        self.color = ColorEditor(default)
        self.color.changed.connect(self.emit_change)
        self._attach(self.color)

    def read(self) -> str:
        return self.color.value()

    def write(self, value: str) -> None:
        self.color.set_value(value)

    def set_accent(self, accent: str) -> None:
        self.color.set_accent(accent)


class LengthField(Field):
    """Pixel length; with ``slider=True`` a slider mirrors the spin box."""

    def __init__(
        self, label: str, maximum: int, default: int, slider: bool = False, parent: QObject | None = None
    ) -> None:
        super().__init__(label, parent)
        self.spin = QSpinBox()
        self.spin.setRange(0, maximum)
        self.spin.setSuffix(" px")
        self.spin.setValue(default)
        self.spin.valueChanged.connect(self._spin_changed)
        self.slider = None
        widgets = [self.spin]
        if slider:
            self.slider = QSlider(Qt.Orientation.Horizontal)
            self.slider.setRange(0, maximum)
            self.slider.setValue(default)
            self.slider.valueChanged.connect(self.spin.setValue)
            widgets.insert(0, self.slider)
        self._attach(row_widget(*widgets))

    def _spin_changed(self, value: int) -> None:
        if self.slider is not None:
            self.slider.blockSignals(True)
            self.slider.setValue(value)
            self.slider.blockSignals(False)
        self.emit_change()

    def read(self) -> int:
        return self.spin.value()

    def write(self, value: int) -> None:
        for widget in (self.spin, self.slider):
            if widget is not None:
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)


class PaddingField(Field):
    def __init__(self, label: str, default: int = 4, parent: QObject | None = None) -> None:
        super().__init__(label, parent)
        self.spins = []
        for side in (self.tr("Top"), self.tr("Right"), self.tr("Bottom"), self.tr("Left")):
            spin = QSpinBox()
            spin.setRange(0, 40)
            spin.setValue(default)
            spin.setToolTip(side)
            spin.valueChanged.connect(self.emit_change)
            self.spins.append(spin)
        self._attach(row_widget(*self.spins))

    def read(self) -> Padding:
        return Padding(*(spin.value() for spin in self.spins))

    def write(self, value: Padding) -> None:
        for spin, side in zip(self.spins, value.to_list()):
            spin.blockSignals(True)
            spin.setValue(side)
            spin.blockSignals(False)


class BackgroundField(Field):
    """Solid color or a two-color linear gradient (extra middle stops are preserved)."""

    DIRECTIONS = ((0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 1.0, 1.0))

    def __init__(self, label: str, parent: QObject | None = None) -> None:
        super().__init__(label, parent)
        self._coords = self.DIRECTIONS[0]
        self._middle: list[GradientStop] = []
        self.mode = QComboBox()
        self.mode.addItems([self.tr("Solid color"), self.tr("Gradient")])
        self.solid = ColorEditor("#ffffff")
        self.direction = QComboBox()
        self.direction.addItems([self.tr("Top to bottom"), self.tr("Left to right"), self.tr("Diagonal")])
        self.start = ColorEditor("#ffffff")
        self.end = ColorEditor("#d0d0d0")

        self.gradient_page = QWidget()
        gradient_form = QFormLayout(self.gradient_page)
        gradient_form.setContentsMargins(0, 0, 0, 0)
        gradient_form.addRow(self.tr("Direction"), self.direction)
        gradient_form.addRow(self.tr("Start"), self.start)
        gradient_form.addRow(self.tr("End"), self.end)
        editor = QWidget()
        layout = QVBoxLayout(editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.mode)
        layout.addWidget(self.solid)
        layout.addWidget(self.gradient_page)
        self._show_page(0)

        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.direction.currentIndexChanged.connect(self._direction_changed)
        for color_editor in (self.solid, self.start, self.end):
            color_editor.changed.connect(self.emit_change)
        self._attach(editor)

    def _show_page(self, index: int) -> None:
        # Show/hide rather than QStackedWidget, which reserves the tallest page's height.
        self.solid.setVisible(index == 0)
        self.gradient_page.setVisible(index == 1)

    def _mode_changed(self, index: int) -> None:
        self._show_page(index)
        self.emit_change()

    def _direction_changed(self, index: int) -> None:
        if index >= 0:
            self._coords = self.DIRECTIONS[index]
        self.emit_change()

    def read(self):
        if self.mode.currentIndex() == 0:
            return self.solid.value()
        stops = [GradientStop(0.0, self.start.value()), *self._middle, GradientStop(1.0, self.end.value())]
        return Gradient(stops, *self._coords)

    def write(self, value) -> None:
        for widget in (self.mode, self.direction):
            widget.blockSignals(True)
        if isinstance(value, Gradient):
            self.mode.setCurrentIndex(1)
            self._show_page(1)
            self._coords = (value.x1, value.y1, value.x2, value.y2)
            known = self._coords in self.DIRECTIONS
            self.direction.setCurrentIndex(self.DIRECTIONS.index(self._coords) if known else -1)
            self.start.set_value(value.stops[0].color)
            self.end.set_value(value.stops[-1].color)
            self._middle = list(value.stops[1:-1])
        else:
            self.mode.setCurrentIndex(0)
            self._show_page(0)
            self.solid.set_value(value)
        for widget in (self.mode, self.direction):
            widget.blockSignals(False)

    def set_accent(self, accent: str) -> None:
        for color_editor in (self.solid, self.start, self.end):
            color_editor.set_accent(accent)
