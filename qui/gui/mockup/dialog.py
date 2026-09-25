"""Mockup of QGIS's options-style dialogs (Options, Layer Properties, Plugin Manager)."""

from __future__ import annotations

from qgis.gui import QgsCollapsibleGroupBox, QgsDoubleSpinBox, QgsScrollArea
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFontComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .common import icon


class MockOptionsDialog(QDialog):
    """Stand-in for ``QgsOptionsDialogBase`` dialogs, showing every common control.

    Keeps the real skeleton: ``mOptionsSplitter`` > ``mOptionsListWidget`` |
    ``mOptionsFrame`` > ``mOptionsStackedWidget``.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("QgsOptionsBase")
        self.setWindowTitle(self.tr("Options — General"))

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setObjectName("mOptionsSplitter")
        splitter.addWidget(self._page_list())

        frame = QFrame()
        frame.setObjectName("mOptionsFrame")
        stack = QStackedWidget(frame)
        stack.setObjectName("mOptionsStackedWidget")
        stack.addWidget(self._general_page())
        QVBoxLayout(frame).addWidget(stack)
        splitter.addWidget(frame)
        splitter.setSizes([190, 570])

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Help
        )
        layout = QVBoxLayout(self)
        layout.addWidget(splitter, 1)
        layout.addWidget(buttons)
        self.resize(780, 580)

    def _page_list(self) -> QListWidget:
        pages = QListWidget()
        pages.setObjectName("mOptionsListWidget")
        pages.setIconSize(QSize(24, 24))
        for icon_name, text in (
            ("general", self.tr("General")),
            ("system", self.tr("System")),
            ("CRS", self.tr("CRS and Transforms")),
            ("attributes", self.tr("Data Sources")),
            ("rendering", self.tr("Rendering")),
            ("overlay", self.tr("Canvas & Legend")),
            ("map_tools", self.tr("Map Tools")),
            ("colors", self.tr("Colors")),
            ("network_and_proxy", self.tr("Network")),
            ("gdal", self.tr("GDAL")),
        ):
            QListWidgetItem(icon(f"propertyicons/{icon_name}"), text, pages)
        disabled = pages.item(pages.count() - 1)
        disabled.setFlags(disabled.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        pages.setCurrentRow(0)
        return pages

    def _general_page(self) -> QgsScrollArea:
        page = QgsScrollArea()
        page.setObjectName("mOptionsScrollArea_01")
        page.setWidgetResizable(True)
        contents = QWidget()
        layout = QVBoxLayout(contents)
        layout.addWidget(self._application_group())
        layout.addWidget(self._project_files_group())
        layout.addWidget(self._tabs())
        layout.addStretch(1)
        page.setWidget(contents)
        return page

    def _application_group(self) -> QgsCollapsibleGroupBox:
        group = QgsCollapsibleGroupBox(self.tr("Application"))
        # The mockup must never write collapse/check state into the user's QGIS settings.
        group.setSaveCollapsedState(False)
        group.setSaveCheckedState(False)
        form = QFormLayout(group)
        theme = QComboBox()
        theme.addItems(["default", "Blend of Gray", "Night Mapping"])
        icon_size = QComboBox()
        icon_size.addItems(["16", "24", "32", "48"])
        icon_size.setCurrentIndex(1)
        size = QgsDoubleSpinBox()
        size.setValue(9.0)
        form.addRow(self.tr("User interface theme"), theme)
        form.addRow(self.tr("Icon size"), icon_size)
        form.addRow(self.tr("Font"), QFontComboBox())
        form.addRow(self.tr("Size"), size)
        news = QCheckBox(self.tr("Show QGIS news feed"))
        news.setChecked(True)
        form.addRow(news)
        form.addRow(QRadioButton(self.tr("Open last project on start")))
        new_project = QRadioButton(self.tr("Start with a new project"))
        new_project.setChecked(True)
        form.addRow(new_project)
        return group

    def _project_files_group(self) -> QGroupBox:
        group = QGroupBox(self.tr("Project files"))
        layout = QVBoxLayout(group)

        row = QHBoxLayout()
        row.addWidget(QLineEdit("C:/Users/Public/Documents/QGIS"))
        row.addWidget(QPushButton(self.tr("Browse…")))
        layout.addLayout(row)

        row = QHBoxLayout()
        locked = QLineEdit(self.tr("Managed by your organization"))
        locked.setEnabled(False)
        reset = QPushButton(self.tr("Reset"))
        reset.setEnabled(False)
        row.addWidget(locked)
        row.addWidget(reset)
        layout.addLayout(row)

        toggle = QPushButton(self.tr("Autosave"))
        toggle.setCheckable(True)
        toggle.setChecked(True)
        layout.addWidget(toggle, 0, Qt.AlignmentFlag.AlignLeft)
        return group

    def _tabs(self) -> QTabWidget:
        tabs = QTabWidget()
        table = QTableWidget(3, 2)
        table.setHorizontalHeaderLabels([self.tr("Variable"), self.tr("Value")])
        for row, (name, value) in enumerate(
            (("qgis_version", "3.40"), ("qgis_platform", "desktop"), ("user_full_name", "Ada Lovelace"))
        ):
            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, QTableWidgetItem(value))
        table.horizontalHeader().setStretchLastSection(True)
        table.selectRow(1)
        tabs.addTab(table, self.tr("Variables"))
        tabs.addTab(QWidget(), self.tr("Environment"))
        tabs.addTab(QWidget(), self.tr("Advanced"))
        tabs.setTabEnabled(2, False)
        return tabs
