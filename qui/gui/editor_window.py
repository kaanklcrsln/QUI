"""The three-pane editor window: component tree | mockup | inspector."""

from __future__ import annotations

import copy
from pathlib import Path

from qgis.core import QgsApplication, QgsSettings
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QFont, QIcon, QKeySequence
from qgis.PyQt.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QToolButton,
    QWidget,
)

from ..compat import QAction, QUndoStack
from ..core.contrast import text_contrast
from ..core.qss_generator import generate_qss
from ..core.selector_registry import COMPONENTS
from ..core.theme_applier import AUTO_APPLY_KEY, ThemeApplier, ui_theme_qss
from ..core.theme_io import (
    FILE_SUFFIX,
    ThemeFileError,
    export_qgis_theme,
    is_qui_export,
    list_presets,
    load_theme,
    qgis_theme_folder_name,
    save_theme,
    with_suffix,
)
from ..core.theme_model import Theme
from .commands import ReplaceTheme, SetGlobalValue, SetStateValue
from .component_tree import ComponentTree
from .confirm_dialog import ConfirmDialog
from .inspector import Inspector
from .mockup.common import icon
from .preview import PreviewPane

REFRESH_DELAY_MS = 40  # coalesce rapid edits (slider drags) into one restyle
LAST_DIR_KEY = "qui/lastThemeDir"
CONFIRM_SECONDS = 15


def _add_all(target, actions) -> None:
    """Add actions to a menu or toolbar; ``None`` adds a separator."""
    for action in actions:
        if action is None:
            target.addSeparator()
        else:
            target.addAction(action)


class EditorWindow(QMainWindow):
    """Top-level editor window, parented to the QGIS main window."""

    def __init__(self, parent: QWidget | None = None, applier: ThemeApplier | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("QuiEditorWindow")
        self.resize(1440, 900)
        # The plugin owns the applier so an applied theme outlives this window.
        self.applier = applier if applier is not None else ThemeApplier()

        # A new theme starts from the UI theme QGIS is currently running.
        self.theme = Theme(base_ui_theme=QgsApplication.themeName())
        self.file_path: Path | None = None
        self.selected: str | None = None
        self._force_close = False
        self.undo_stack = QUndoStack(self)
        self.tree = ComponentTree(parent=self)
        self.preview = PreviewPane(self)
        self.inspector = Inspector(self)
        self.inspector.global_panel.load(self.theme)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.preview)
        splitter.addWidget(self.inspector)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([230, 770, 440])  # inspector wide enough for five state tabs
        self.setCentralWidget(splitter)
        self._build_actions()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(REFRESH_DELAY_MS)
        self._refresh_timer.timeout.connect(self.refresh_preview)

        self.tree.component_selected.connect(self.select_component)
        self.preview.picker.picked.connect(self.select_component)
        self.inspector.component_panel.changed.connect(self._component_edited)
        self.inspector.component_panel.state_changed.connect(self._update_contrast)
        self.inspector.global_panel.changed.connect(self.set_global_value)
        self.inspector.global_panel.spread_radius_requested.connect(self.spread_radius)
        self.undo_stack.cleanChanged.connect(self._clean_changed)
        self._update_title()
        self.refresh_preview()

    def _action(self, text: str, slot, icon_name: str = "", shortcut=None) -> QAction:
        action = QAction(icon(icon_name) if icon_name else QIcon(), text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        return action

    def _build_actions(self) -> None:
        keys = QKeySequence.StandardKey
        new = self._action(self.tr("New Theme"), self.new_theme, "mActionFileNew", keys.New)
        # Slots are bound methods, never lambdas capturing self: PyQt holds bound methods
        # weakly but lambdas strongly, which would keep this window's wrapper alive forever.
        open_ = self._action(self.tr("Open…"), self._open_clicked, "mActionFileOpen", keys.Open)
        save = self._action(self.tr("Save"), self.save_theme, "mActionFileSave", keys.Save)
        save_as = self._action(self.tr("Save As…"), self._save_as_clicked, "mActionFileSaveAs", keys.SaveAs)
        export_qss = self._action(self.tr("Export Stylesheet (.qss)…"), self._export_clicked)
        export_theme = self._action(self.tr("Export as QGIS Theme…"), self._export_theme_clicked)
        close = self._action(self.tr("Close"), self.close, shortcut=keys.Close)
        undo = self.undo_stack.createUndoAction(self, self.tr("Undo"))
        undo.setIcon(icon("mActionUndo"))
        undo.setShortcut(keys.Undo)
        redo = self.undo_stack.createRedoAction(self, self.tr("Redo"))
        redo.setIcon(icon("mActionRedo"))
        redo.setShortcut(keys.Redo)

        file_menu = self.menuBar().addMenu(self.tr("&File"))
        _add_all(file_menu, (new, open_, None, save, save_as, None, export_theme, export_qss, None, close))
        edit_menu = self.menuBar().addMenu(self.tr("&Edit"))
        edit_menu.addAction(undo)
        edit_menu.addAction(redo)
        apply = self._action(self.tr("Apply to QGIS"), self.apply_to_qgis)
        apply.setIcon(QIcon(str(Path(__file__).resolve().parents[1] / "resources" / "icons" / "qui.png")))
        apply.setShortcut(QKeySequence("Ctrl+Return"))
        restore = self._action(self.tr("Restore Original QGIS Look"), self.restore_qgis_look)
        self.auto_apply_action = QAction(self.tr("Re-apply Kept Theme When QGIS Starts"), self)
        self.auto_apply_action.setCheckable(True)
        self.auto_apply_action.setChecked(QgsSettings().value(AUTO_APPLY_KEY, True, type=bool))
        self.auto_apply_action.toggled.connect(self._auto_apply_toggled)
        qgis_menu = self.menuBar().addMenu(self.tr("&QGIS"))
        _add_all(qgis_menu, (apply, restore, None, self.auto_apply_action))

        self.presets_menu = self.menuBar().addMenu(self.tr("&Presets"))
        for name, path in list_presets().items():
            self.presets_menu.addAction(name).setData(str(path))
        self.presets_menu.triggered.connect(self._preset_clicked)

        toolbar = self.addToolBar(self.tr("Theme"))
        toolbar.setObjectName("quiThemeToolbar")
        _add_all(toolbar, (new, open_, save, None, undo, redo))
        presets_button = QToolButton(toolbar)
        presets_button.setText(self.tr("Presets"))
        presets_button.setMenu(self.presets_menu)
        presets_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addSeparator()
        toolbar.addWidget(presets_button)
        toolbar.addSeparator()
        toolbar.addAction(apply)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

    def _open_clicked(self) -> None:
        self.open_theme()

    def _save_as_clicked(self) -> None:
        self.save_theme_as()

    def _export_clicked(self) -> None:
        self.export_qss()

    def _export_theme_clicked(self) -> None:
        self.export_qgis_theme()

    def _preset_clicked(self, action: QAction) -> None:
        self.apply_preset(Path(action.data()))

    def _clean_changed(self, clean: bool) -> None:
        self.setWindowModified(not clean)

    def _auto_apply_toggled(self, enabled: bool) -> None:
        QgsSettings().setValue(AUTO_APPLY_KEY, enabled)

    # Applying to QGIS -----------------------------------------------------------------

    def apply_to_qgis(self) -> ConfirmDialog:
        """Apply the theme to the whole application, then ask to keep it (auto-revert)."""
        self.applier.apply(self.theme)
        self.confirm_dialog = ConfirmDialog(CONFIRM_SECONDS, self.applier.original_font, self)
        self.confirm_dialog.finished.connect(self._confirm_finished)
        self.confirm_dialog.open()
        return self.confirm_dialog

    def _confirm_finished(self, result: int) -> None:
        if result == ConfirmDialog.DialogCode.Accepted:
            self.applier.keep()
        else:
            self.applier.revert()

    def restore_qgis_look(self) -> None:
        self.applier.restore()

    # Selection ------------------------------------------------------------------------

    def select_component(self, component_id: str) -> None:
        """Select a component everywhere: tree, mockup highlight, inspector."""
        component = COMPONENTS[component_id]
        self.selected = component_id
        self.tree.select(component_id)
        visible = self.preview.highlight(component) > 0
        self.inspector.setCurrentIndex(0)
        self.inspector.component_panel.show_component(
            component, self.theme.component(component_id), self.theme.global_style.accent, visible
        )
        self._update_contrast()

    def _update_contrast(self) -> None:
        if self.selected is not None:
            panel = self.inspector.component_panel
            panel.show_contrast(text_contrast(self.theme, self.selected, panel.current_state()))

    # Edits: public methods push undo commands; apply_* do the change -----------------

    def set_state_value(self, component_id: str, state: str, field: str, value) -> None:
        """Set one property of one component state (``None`` = not set), undoably."""
        old = getattr(self.theme.component(component_id).state(state), field)
        if old == value:
            return
        label = self.inspector.component_panel.fields[field].check.text()
        self.undo_stack.push(SetStateValue(self, (component_id, state, field), old, value, label))

    def apply_state_value(
        self, component_id: str, state: str, field: str, value, reveal: bool = False
    ) -> None:
        setattr(self.theme.component(component_id).state(state), field, value)
        if reveal:  # undo/redo: show what changed
            self.select_component(component_id)
            self.inspector.component_panel.set_state(state)
            self.inspector.component_panel.reload()
        self.schedule_refresh()

    def set_global_value(self, field: str, value) -> None:
        """Set a theme-wide value undoably; see ``GlobalPanel`` for the field names."""
        old = self._global_value(field)
        if old != value:
            self.undo_stack.push(SetGlobalValue(self, (field,), old, value, self.tr("Global setting")))

    def _global_value(self, field: str):
        if field == "base_ui_theme":
            return self.theme.base_ui_theme
        if field in ("font_family", "font_size"):
            return self.theme.font.family if field == "font_family" else self.theme.font.point_size
        return getattr(self.theme.global_style, field)

    def apply_global_value(self, field: str, value) -> None:
        if field == "base_ui_theme":
            self.theme.base_ui_theme = value
        elif field == "font_family":
            self.theme.font.family = value
        elif field == "font_size":
            self.theme.font.point_size = value
        else:
            setattr(self.theme.global_style, field, value)
        self.inspector.global_panel.load(self.theme)
        self.inspector.component_panel.set_accent(self.theme.global_style.accent)
        self.schedule_refresh()

    def spread_radius(self) -> None:
        """Copy the global radius into every component whose normal state has a background or border."""
        before = self.theme.to_dict()
        radius = self.theme.global_style.radius
        after = copy.deepcopy(before)
        for component_id, states in after["components"].items():
            normal = states.get("normal", {})
            styled = "background" in normal or normal.get("border_width")
            if styled and component_id in COMPONENTS and COMPONENTS[component_id].selectors:
                normal["border_radius"] = radius
        if after != before:
            self.undo_stack.push(ReplaceTheme(self, before, after, self.tr("Apply corner radius")))

    def apply_preset(self, path: Path) -> None:
        """Replace the current theme with a bundled preset (undoable)."""
        try:
            preset = load_theme(path)
        except ThemeFileError as error:
            QMessageBox.warning(self, self.tr("Preset"), str(error))
            return
        self.undo_stack.push(ReplaceTheme(self, self.theme.to_dict(), preset.to_dict(), preset.name))

    def apply_theme_dict(self, data: dict) -> None:
        self.replace_theme(Theme.from_dict(data))

    def replace_theme(self, theme: Theme) -> None:
        """Show *theme* everywhere (inspector, preview, title); does not touch the undo stack."""
        self.theme = theme
        self.inspector.global_panel.load(theme)
        if self.selected is not None:
            self.select_component(self.selected)
        self._update_title()
        self.schedule_refresh()

    def _component_edited(self, state: str, field: str, value) -> None:
        if self.selected is not None:
            self.set_state_value(self.selected, state, field, value)

    # Files ----------------------------------------------------------------------------

    def _dialog_dir(self) -> str:
        return str(
            self.file_path.parent if self.file_path else QgsSettings().value(LAST_DIR_KEY, str(Path.home()))
        )

    def new_theme(self) -> None:
        if self.maybe_save():
            self._start_document(Theme(base_ui_theme=QgsApplication.themeName()), None)

    def open_theme(self, path: str | Path | None = None) -> bool:
        if not self.maybe_save():
            return False
        if path is None:
            path, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("Open Theme"),
                self._dialog_dir(),
                self.tr("QUI themes (*%1)").replace("%1", FILE_SUFFIX),
            )
            if not path:
                return False
        try:
            theme = load_theme(path)
        except ThemeFileError as error:
            QMessageBox.warning(self, self.tr("Open Theme"), str(error))
            return False
        self._start_document(theme, Path(path))
        return True

    def save_theme(self) -> bool:
        return self.save_theme_as(self.file_path) if self.file_path else self.save_theme_as()

    def save_theme_as(self, path: str | Path | None = None) -> bool:
        if path is None:
            suggested = str(Path(self._dialog_dir()) / with_suffix(self.theme.name).name)
            path, _ = QFileDialog.getSaveFileName(
                self, self.tr("Save Theme"), suggested, self.tr("QUI themes (*%1)").replace("%1", FILE_SUFFIX)
            )
            if not path:
                return False
        path = with_suffix(path)
        try:
            save_theme(self.theme, path)
        except OSError as error:
            QMessageBox.warning(self, self.tr("Save Theme"), str(error))
            return False
        self.file_path = path
        QgsSettings().setValue(LAST_DIR_KEY, str(path.parent))
        self.undo_stack.setClean()
        self._update_title()
        return True

    def export_qss(self, path: str | Path | None = None) -> bool:
        """Write the complete stylesheet QGIS would get (base UI theme + QUI rules)."""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self, self.tr("Export Stylesheet"), self._dialog_dir(), self.tr("Qt stylesheets (*.qss)")
            )
            if not path:
                return False
        try:
            Path(path).write_text(
                generate_qss(self.theme, ui_theme_qss(self.theme.base_ui_theme)), encoding="utf-8"
            )
        except OSError as error:
            QMessageBox.warning(self, self.tr("Export Stylesheet"), str(error))
            return False
        return True

    def export_qgis_theme(self, name: str | None = None, themes_dir: Path | None = None) -> Path | None:
        """Export as a QGIS UI theme in the profile, selectable in Options without QUI."""
        title = self.tr("Export as QGIS Theme")
        if name is None:
            name, ok = QInputDialog.getText(self, title, self.tr("Theme name:"), text=self.theme.name)
            if not ok or not name.strip():
                return None
        themes = QgsApplication.uiThemes()
        if name in themes and not is_qui_export(Path(themes[name])):
            QMessageBox.warning(self, title, self.tr("“%1” is taken by another theme.").replace("%1", name))
            return None
        # Ask QGIS where it looks for user themes; the location differs between QGIS versions.
        themes_dir = themes_dir or Path(QgsApplication.userThemesFolder())
        folder = themes_dir / qgis_theme_folder_name(name)
        base_dir = themes.get(self.theme.base_ui_theme) or None
        try:
            export_qgis_theme(self.theme, folder, base_dir)
        except (OSError, ThemeFileError) as error:
            QMessageBox.warning(self, title, str(error))
            return None
        QMessageBox.information(
            self,
            title,
            self.tr(
                "Exported to %1.\n\nChoose “%2” in Settings → Options → General → UI Theme. "
                "The program font is not part of QGIS themes."
            )
            .replace("%1", str(folder))
            .replace("%2", folder.name),
        )
        return folder

    def _start_document(self, theme: Theme, path: Path | None) -> None:
        self.file_path = path
        self.undo_stack.clear()
        self.replace_theme(theme)

    def maybe_save(self) -> bool:
        """Ask to save unsaved changes; False means the user cancelled."""
        if self.undo_stack.isClean():
            return True
        buttons = QMessageBox.StandardButton
        answer = QMessageBox.question(
            self,
            self.tr("Unsaved Changes"),
            self.tr("Save the changes to “%1”?").replace("%1", self.theme.name),
            buttons.Save | buttons.Discard | buttons.Cancel,
        )
        if answer == buttons.Save:
            return self.save_theme()
        return answer == buttons.Discard

    def force_close(self) -> None:
        """Close without asking (plugin unload)."""
        self._force_close = True
        self.close()

    def closeEvent(self, event) -> None:
        if self._force_close or self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def _update_title(self) -> None:
        name = self.file_path.name if self.file_path else self.theme.name
        self.setWindowTitle(f"{name}[*] — {self.tr('QUI - Quantum User Interfaces')}")

    # Preview --------------------------------------------------------------------------

    def schedule_refresh(self) -> None:
        """Every theme change ends here: restyle the preview soon, update contrast now."""
        self._refresh_timer.start()
        self._update_contrast()

    def preview_qss(self) -> str:
        """The stylesheet QGIS would get for the current theme, plus the main-window cascade."""
        qss = generate_qss(self.theme, ui_theme_qss(self.theme.base_ui_theme))
        # The mockups live in a graphics scene, outside the QGIS main window, so its own
        # stylesheet (e.g. "QGroupBox{ font-weight: 600; }") would not cascade into them.
        parent = self.parentWidget()
        if parent is not None and parent.styleSheet():
            qss += f"\n/* QGIS main-window stylesheet */\n{parent.styleSheet()}\n"
        return qss

    def preview_font(self) -> QFont:
        """The global font as QGIS would get it; unset parts inherit the application font."""
        font = QFont()
        if self.theme.font.family:
            font.setFamily(self.theme.font.family)
        if self.theme.font.point_size:
            font.setPointSizeF(self.theme.font.point_size)
        return font

    def refresh_preview(self) -> None:
        """Regenerate the QSS and font from the theme and show them on the mockups."""
        self._refresh_timer.stop()
        self.preview.apply_style(self.preview_qss(), self.preview_font())
        QTimer.singleShot(0, self.preview.refresh_highlight)  # after the new layout settles
