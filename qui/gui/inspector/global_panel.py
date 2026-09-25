"""Inspector tab for theme-wide settings and the global program font."""

from __future__ import annotations

from qgis.core import QgsApplication
from qgis.gui import QgsColorButton
from qgis.PyQt.QtCore import QObject, Qt, pyqtSignal
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFontComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.theme_model import Theme
from .fields import Field, row_widget, to_hex, to_qcolor


class FontFamilyField(Field):
    """Installed font families only (QFontComboBox lists QFontDatabase)."""

    def __init__(self, label: str, parent: QObject | None = None) -> None:
        super().__init__(label, parent)
        self.combo = QFontComboBox()
        self.combo.currentFontChanged.connect(self.emit_change)
        self._attach(self.combo)

    def read(self) -> str:
        return self.combo.currentFont().family()

    def write(self, value: str) -> None:
        self.combo.blockSignals(True)
        self.combo.setCurrentFont(QFont(value))  # setCurrentText would only change the edit text
        self.combo.blockSignals(False)


class FontSizeField(Field):
    def __init__(self, label: str, parent: QObject | None = None) -> None:
        super().__init__(label, parent)
        self.spin = QDoubleSpinBox()
        self.spin.setRange(4, 40)
        self.spin.setSingleStep(0.5)
        self.spin.setSuffix(" pt")
        self.spin.setValue(9)
        self.spin.valueChanged.connect(self.emit_change)
        self._attach(self.spin)

    def read(self) -> float:
        return self.spin.value()

    def write(self, value: float) -> None:
        self.spin.blockSignals(True)
        self.spin.setValue(value)
        self.spin.blockSignals(False)


class GlobalPanel(QWidget):
    """Emits ``changed(field, value)``; fields: base_ui_theme, accent, radius, opacity,
    font_family, font_size. ``spread_radius_requested`` asks to copy the radius."""

    changed = pyqtSignal(str, object)
    spread_radius_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_theme = QComboBox()
        themes = sorted(QgsApplication.uiThemes(), key=lambda name: (name != "default", name))
        self.base_theme.addItems(themes)
        self.base_theme.currentTextChanged.connect(lambda text: self.changed.emit("base_ui_theme", text))
        self.accent = QgsColorButton()
        self.accent.colorChanged.connect(lambda color: self.changed.emit("accent", to_hex(color)))
        self.radius = QSpinBox()
        self.radius.setRange(0, 40)
        self.radius.setSuffix(" px")
        self.radius.valueChanged.connect(lambda value: self.changed.emit("radius", value))
        spread = QPushButton(self.tr("Apply to styled components"))
        spread.setToolTip(
            self.tr(
                "Sets this corner radius on every component whose normal state already has a background "
                "or a border. Radius alone would replace the native look of unstyled widgets."
            )
        )
        spread.clicked.connect(self.spread_radius_requested)
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity_label = QLabel()
        self.opacity_label.setMinimumWidth(40)
        self.opacity.valueChanged.connect(self._opacity_changed)

        theme_box = QGroupBox(self.tr("Theme"))
        form = QFormLayout(theme_box)
        form.addRow(self.tr("Base QGIS theme"), self.base_theme)
        form.addRow(self.tr("Accent color"), self.accent)
        form.addRow(self.tr("Corner radius"), row_widget(self.radius, spread))
        form.addRow(self.tr("Background opacity"), row_widget(self.opacity, self.opacity_label))

        self.font_family = FontFamilyField(self.tr("Family"), self)
        self.font_size = FontSizeField(self.tr("Size"), self)
        self.font_family.changed.connect(lambda value: self.changed.emit("font_family", value))
        self.font_size.changed.connect(lambda value: self.changed.emit("font_size", value))
        font_box = QGroupBox(self.tr("Program font"))
        font_form = QFormLayout(font_box)
        font_form.addRow(self.font_family.check, self.font_family.editor)
        font_form.addRow(self.font_size.check, self.font_size.editor)
        note = QLabel(self.tr("Unchecked values keep QGIS's own font."))
        note.setWordWrap(True)
        font_form.addRow(note)

        layout = QVBoxLayout(self)
        layout.addWidget(theme_box)
        layout.addWidget(font_box)
        layout.addStretch(1)

    def load(self, theme: Theme) -> None:
        """Show *theme*'s global values without emitting ``changed``."""
        for widget in (self.base_theme, self.accent, self.radius, self.opacity):
            widget.blockSignals(True)
        self.base_theme.setCurrentText(theme.base_ui_theme)
        self.accent.setColor(to_qcolor(theme.global_style.accent))
        self.radius.setValue(theme.global_style.radius)
        self.opacity.setValue(round(theme.global_style.opacity * 100))
        self.opacity_label.setText(f"{self.opacity.value()}%")
        for widget in (self.base_theme, self.accent, self.radius, self.opacity):
            widget.blockSignals(False)
        self.font_family.set_value(theme.font.family)
        self.font_size.set_value(theme.font.point_size)

    def _opacity_changed(self, value: int) -> None:
        self.opacity_label.setText(f"{value}%")
        self.changed.emit("opacity", value / 100)
