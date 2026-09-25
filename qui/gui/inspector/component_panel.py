"""Inspector tab for the selected component: state tabs + nullable property rows."""

from __future__ import annotations

from functools import partial

from qgis.PyQt.QtCore import QCoreApplication, Qt, pyqtSignal
from qgis.PyQt.QtWidgets import QFormLayout, QLabel, QStackedWidget, QTabBar, QVBoxLayout, QWidget

from ...core.selector_registry import Component
from ...core.theme_model import ComponentStyle
from .fields import BackgroundField, ColorField, Field, LengthField, PaddingField


class ComponentPanel(QWidget):
    """Edits one component; emits ``changed(state, field, value)`` for every edit."""

    changed = pyqtSignal(str, str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._style: ComponentStyle | None = None
        self.title = QLabel()
        font = self.title.font()
        font.setBold(True)
        font.setPointSizeF(font.pointSizeF() * 1.2)
        self.title.setFont(font)
        self.selectors = QLabel()
        self.selectors.setWordWrap(True)
        self.selectors.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.note = QLabel(self.tr("Not visible in the mockup; the style still applies in QGIS."))
        self.note.setWordWrap(True)
        self.state_bar = QTabBar()
        self.state_bar.setExpanding(False)
        self.state_bar.currentChanged.connect(self._load)

        self.fields: dict[str, Field] = {
            "background": BackgroundField(self.tr("Background"), self),
            "color": ColorField(self.tr("Text color"), "#000000", self),
            "border_width": LengthField(self.tr("Border width"), maximum=20, default=1, parent=self),
            "border_color": ColorField(self.tr("Border color"), "#808080", self),
            "border_radius": LengthField(
                self.tr("Corner radius"), maximum=40, default=4, slider=True, parent=self
            ),
            "padding": PaddingField(self.tr("Padding"), parent=self),
        }
        form = QFormLayout()
        for name, field in self.fields.items():
            form.addRow(field.check, field.editor)
            field.changed.connect(partial(self._field_changed, name))

        editor_page = QWidget()
        layout = QVBoxLayout(editor_page)
        for widget in (self.title, self.selectors, self.note, self.state_bar):
            layout.addWidget(widget)
        layout.addLayout(form)
        layout.addStretch(1)
        hint = QLabel(self.tr("Click a part of the mockup or pick a component on the left."))
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        self.pages = QStackedWidget(self)
        self.pages.addWidget(hint)
        self.pages.addWidget(editor_page)
        QVBoxLayout(self).addWidget(self.pages)

    def state_labels(self) -> dict[str, str]:
        return {
            "normal": self.tr("Normal"),
            "hover": self.tr("Hover"),
            "pressed": self.tr("Pressed"),
            "selected": self.tr("Selected"),
            "checked": self.tr("Checked"),
            "disabled": self.tr("Disabled"),
        }

    def show_component(self, component: Component, style: ComponentStyle, accent: str, visible: bool) -> None:
        """Show *component*'s *style*; keeps the current state tab when the new component has it."""
        self.title.setText(QCoreApplication.translate("QuiComponents", component.label))
        self.selectors.setText("\n".join(component.selectors))
        self.note.setVisible(not visible)
        previous = self.current_state()
        labels = self.state_labels()
        self.state_bar.blockSignals(True)
        while self.state_bar.count():
            self.state_bar.removeTab(0)
        for state in component.states:
            self.state_bar.setTabData(self.state_bar.addTab(labels[state]), state)
        self.state_bar.setCurrentIndex(
            component.states.index(previous) if previous in component.states else 0
        )
        self.state_bar.blockSignals(False)
        self._style = style
        self.set_accent(accent)
        self._load()
        self.pages.setCurrentIndex(1)

    def current_state(self) -> str | None:
        index = self.state_bar.currentIndex()
        return self.state_bar.tabData(index) if index >= 0 else None

    def reload(self) -> None:
        """Re-read the shown style (after undo/redo or a bulk change)."""
        self._load()

    def set_accent(self, accent: str) -> None:
        for field in self.fields.values():
            field.set_accent(accent)

    def _load(self) -> None:
        state_style = self._style.states.get(self.current_state()) if self._style is not None else None
        for name, field in self.fields.items():
            field.set_value(getattr(state_style, name) if state_style is not None else None)

    def _field_changed(self, name: str, value) -> None:
        self.changed.emit(self.current_state(), name, value)
