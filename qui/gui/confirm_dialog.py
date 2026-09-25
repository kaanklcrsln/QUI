"""After "Apply to QGIS": keep the new look, or revert automatically after a countdown."""

from __future__ import annotations

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

# The dialog's own sheet beats the application stylesheet, so it stays readable
# however unreadable the theme that was just applied is.
NEUTRAL_QSS = """
QDialog { background-color: #ffffff; }
QLabel { color: #1a1a1a; background-color: transparent; }
QPushButton { color: #1a1a1a; background-color: #f0f0f0; border: 1px solid #8a8a8a;
              border-radius: 3px; padding: 5px 16px; }
QPushButton:hover { background-color: #e2e2e2; }
QPushButton:default { border: 2px solid #1a5fd0; }
"""


class ConfirmDialog(QDialog):
    """Only an explicit "Keep changes" accepts; timeout, Esc, Enter or closing revert."""

    def __init__(self, seconds: int, font: QFont | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("QuiConfirmDialog")
        self.setWindowTitle(self.tr("QUI"))
        self.setStyleSheet(NEUTRAL_QSS)
        if font is not None:
            self.setFont(font)  # the original font, in case the theme's font is unusable
        self.remaining = seconds
        self.message = QLabel(self)
        self.keep_button = QPushButton(self.tr("Keep changes"), self)
        self.revert_button = QPushButton(self.tr("Revert"), self)
        self.revert_button.setDefault(True)
        self.keep_button.setAutoDefault(False)
        self.keep_button.clicked.connect(self.accept)
        self.revert_button.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.keep_button)
        buttons.addWidget(self.revert_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.message)
        layout.addLayout(buttons)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self._update_message()

    def _tick(self) -> None:
        self.remaining -= 1
        if self.remaining <= 0:
            self.timer.stop()
            self.reject()
        else:
            self._update_message()

    def _update_message(self) -> None:
        self.message.setText(
            self.tr("The theme is now applied to QGIS.\nKeep it? Reverting in %1 s.").replace(
                "%1", str(self.remaining)
            )
        )

    def done(self, result: int) -> None:
        self.timer.stop()
        super().done(result)
