"""Plugin lifecycle: register the menu/toolbar action and open the editor window."""

from __future__ import annotations

from pathlib import Path

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon

try:  # Qt6 moved QAction to QtGui
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction

from .gui.editor_window import EditorWindow

PLUGIN_DIR = Path(__file__).resolve().parent
ICON_PATH = PLUGIN_DIR / "resources" / "icons" / "qui.svg"


class QuiPlugin:
    """Owns the QUI action and the (lazily created) editor window."""

    def __init__(self, iface) -> None:
        self.iface = iface
        self.action: QAction | None = None
        self.window: EditorWindow | None = None
        self.menu_name = self.tr("&QUI")

    @staticmethod
    def tr(text: str) -> str:
        """Translate *text* in the ``QuiPlugin`` context."""
        return QCoreApplication.translate("QuiPlugin", text)

    def initGui(self) -> None:
        """Called by QGIS when the plugin is enabled."""
        self.action = QAction(QIcon(str(ICON_PATH)), self.tr("QUI Theme Editor…"), self.iface.mainWindow())
        self.action.setObjectName("quiOpenEditor")
        self.action.triggered.connect(self.open_editor)
        self.iface.addPluginToMenu(self.menu_name, self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self) -> None:
        """Called by QGIS when the plugin is disabled or uninstalled."""
        if self.window is not None:
            self.window.close()
            self.window.deleteLater()
            self.window = None
        if self.action is not None:
            self.iface.removePluginMenu(self.menu_name, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

    def open_editor(self) -> None:
        """Show the editor window, creating it on first use."""
        if self.window is None:
            self.window = EditorWindow(self.iface.mainWindow())
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
