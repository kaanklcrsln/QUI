"""Plugin lifecycle: menu/toolbar actions, the editor window, and restoring QGIS's look."""

from __future__ import annotations

from pathlib import Path

from qgis.core import Qgis, QgsApplication, QgsMessageLog
from qgis.PyQt.QtCore import QCoreApplication, QTimer, QTranslator
from qgis.PyQt.QtGui import QIcon

from .compat import QAction
from .core.theme_applier import ThemeApplier, stored_theme
from .gui.editor_window import EditorWindow

PLUGIN_DIR = Path(__file__).resolve().parent
ICON_PATH = PLUGIN_DIR / "resources" / "icons" / "qui.png"


class QuiPlugin:
    """Owns the actions, the (lazily created) editor window and the theme applier."""

    def __init__(self, iface) -> None:
        self.iface = iface
        # Install the translation before any tr() call; QGIS's locale, e.g. "tr" or "pt_BR".
        self.translator: QTranslator | None = None
        locale = QgsApplication.locale()
        for code in (locale, locale[:2]):
            qm = PLUGIN_DIR / "i18n" / f"qui_{code}.qm"
            translator = QTranslator()
            if qm.is_file() and translator.load(str(qm)):
                self.translator = translator
                QCoreApplication.installTranslator(translator)
                break
        self.action: QAction | None = None
        self.restore_action: QAction | None = None
        self.window: EditorWindow | None = None
        self.applier = ThemeApplier()
        self.menu_name = self.tr("&QUI")

    @staticmethod
    def tr(text: str) -> str:
        """Translate *text* in the ``QuiPlugin`` context."""
        return QCoreApplication.translate("QuiPlugin", text)

    def initGui(self) -> None:
        """Called by QGIS when the plugin is enabled."""
        main_window = self.iface.mainWindow()
        self.action = QAction(QIcon(str(ICON_PATH)), self.tr("QUI Theme Editor…"), main_window)
        self.action.setObjectName("quiOpenEditor")
        self.action.triggered.connect(self.open_editor)
        # Reachable without the editor, e.g. when an applied theme turned out unusable.
        self.restore_action = QAction(self.tr("Restore Original QGIS Look"), main_window)
        self.restore_action.setObjectName("quiRestoreLook")
        self.restore_action.triggered.connect(self.restore_look)
        self.iface.addPluginToMenu(self.menu_name, self.action)
        self.iface.addPluginToMenu(self.menu_name, self.restore_action)
        self.iface.addToolBarIcon(self.action)
        # After QGIS has applied its own UI theme and font.
        QTimer.singleShot(0, self.apply_stored_theme)

    def unload(self) -> None:
        """Called when the plugin is disabled, reloaded or uninstalled, and when QGIS exits."""
        # Back to the exact original look, but remember the kept theme for the next start.
        self.applier.restore(forget=False)
        if self.window is not None:
            self.window.force_close()  # no "save changes?" prompt while QGIS unloads plugins
            self.window.deleteLater()
            self.window = None
        for action in (self.action, self.restore_action):
            if action is not None:
                self.iface.removePluginMenu(self.menu_name, action)
                action.deleteLater()
        if self.action is not None:
            self.iface.removeToolBarIcon(self.action)
        self.action = self.restore_action = None
        if self.translator is not None:
            QCoreApplication.removeTranslator(self.translator)
            self.translator = None

    def apply_stored_theme(self) -> None:
        """Re-apply the theme the user kept last time (unless auto-apply is off)."""
        if self.action is None:  # unloaded before the timer fired
            return
        theme = stored_theme()
        if theme is None:
            return
        try:
            self.applier.apply(theme)
            self.applier.keep()
        except Exception as error:  # never block QGIS start-up because of a theme
            self.applier.restore(forget=False)
            QgsMessageLog.logMessage(
                f"Could not apply the kept theme: {error}", "QUI", Qgis.MessageLevel.Warning
            )

    def restore_look(self) -> None:
        self.applier.restore()

    def open_editor(self) -> None:
        """Show the editor window, creating it on first use."""
        if self.window is None:
            self.window = EditorWindow(self.iface.mainWindow(), self.applier)
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
