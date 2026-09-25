"""Mockup of the QGIS main window (``QgisApp``) with sample content."""

from __future__ import annotations

from qgis.core import Qgis, QgsLayerTree, QgsLayerTreeModel, QgsVectorLayer
from qgis.gui import QgsDockWidget, QgsDoubleSpinBox, QgsLayerTreeView, QgsMessageBar, QgsScaleComboBox
from qgis.PyQt.QtCore import QPointF, QSize, Qt
from qgis.PyQt.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF, QStandardItem, QStandardItemModel
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QStatusBar,
    QToolBar,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ..picker import PICKABLE_PROPERTY
from .common import add_action, icon


class MockMainWindow(QMainWindow):
    """Stand-in for ``QgisApp``: menus, toolbars, Layers/Browser panels, map, status bar.

    objectNames match real QGIS (``menubar``, ``mFileToolBar``, ``Layers``, ``Browser``,
    ``theLayerTreeView``, ``statusbar`` ...), so the same selectors hit both.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("QgisApp")
        self.setWindowTitle(self.tr("Untitled Project — QGIS"))
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
        )
        self._build_menus()
        self._build_toolbars()
        self._build_central()
        self._build_docks()
        self._build_statusbar()
        self.resize(1200, 760)

    # Menus -----------------------------------------------------------------------------

    def _menu(self, object_name: str, title: str, parent: QMenu | None = None) -> QMenu:
        menu = (parent or self.menuBar()).addMenu(title)
        menu.setObjectName(object_name)
        return menu

    def _build_menus(self) -> None:
        self.menuBar().setObjectName("menubar")

        project = self._menu("mProjectMenu", self.tr("&Project"))
        add_action(project, "mActionFileNew", self.tr("New"))
        add_action(project, "mActionFileOpen", self.tr("Open…"))
        recent = self._menu("mRecentProjectsMenu", self.tr("Open Recent"), project)
        add_action(recent, None, "world_overview.qgz")
        add_action(recent, None, "city_planning.qgz")
        project.addSeparator()
        add_action(project, "mActionFileSave", self.tr("Save"))
        add_action(project, "mActionFileSaveAs", self.tr("Save As…"))
        project.addSeparator()
        add_action(project, "mActionLayoutManager", self.tr("Layout Manager…"))
        project.addSeparator()
        add_action(project, "mActionFileExit", self.tr("Exit QGIS"))

        edit = self._menu("mEditMenu", self.tr("&Edit"))
        add_action(edit, "mActionUndo", self.tr("Undo"), enabled=False)
        add_action(edit, "mActionRedo", self.tr("Redo"), enabled=False)
        edit.addSeparator()
        add_action(edit, "mActionEditCut", self.tr("Cut Features"))
        add_action(edit, "mActionEditCopy", self.tr("Copy Features"))
        add_action(edit, "mActionEditPaste", self.tr("Paste Features"), enabled=False)
        edit.addSeparator()
        add_action(edit, "mActionToggleEditing", self.tr("Toggle Editing"), checked=False)

        view = self._menu("mViewMenu", self.tr("&View"))
        add_action(view, "mActionNewMap", self.tr("New Map View"))
        view.addSeparator()
        add_action(view, "mActionPan", self.tr("Pan Map"), checked=True)
        add_action(view, "mActionZoomIn", self.tr("Zoom In"))
        add_action(view, "mActionZoomOut", self.tr("Zoom Out"))
        view.addSeparator()
        panels = self._menu("mPanelMenu", self.tr("Panels"), view)
        add_action(panels, None, self.tr("Browser"), checked=True)
        add_action(panels, None, self.tr("Layers"), checked=True)
        add_action(panels, None, self.tr("Layer Styling"), checked=False)
        toolbars = self._menu("mToolbarMenu", self.tr("Toolbars"), view)
        add_action(toolbars, None, self.tr("Project Toolbar"), checked=True)
        add_action(toolbars, None, self.tr("Map Navigation Toolbar"), checked=True)
        add_action(view, "mActionMapTips", self.tr("Show Map Tips"), checked=False)

        layer = self._menu("mLayerMenu", self.tr("&Layer"))
        add_action(layer, "mActionDataSourceManager", self.tr("Data Source Manager"))
        add_layer = self._menu("mAddLayerMenu", self.tr("Add Layer"), layer)
        add_action(add_layer, "mActionAddOgrLayer", self.tr("Add Vector Layer…"))
        add_action(add_layer, "mActionAddRasterLayer", self.tr("Add Raster Layer…"))
        layer.addSeparator()
        add_action(layer, "mActionOpenTable", self.tr("Open Attribute Table"))

        settings = self._menu("mSettingsMenu", self.tr("&Settings"))
        add_action(settings, None, self.tr("Style Manager…"))
        add_action(settings, "mActionOptions", self.tr("Options…"))

        plugins = self._menu("mPluginMenu", self.tr("&Plugins"))
        add_action(plugins, "mActionShowPluginManager", self.tr("Manage and Install Plugins…"))
        add_action(plugins, None, self.tr("Python Console"))

        for object_name, title, entry in (
            ("mVectorMenu", self.tr("Vect&or"), self.tr("Geoprocessing Tools")),
            ("mRasterMenu", self.tr("&Raster"), self.tr("Raster Calculator…")),
            ("mDatabaseMenu", self.tr("&Database"), self.tr("DB Manager")),
            ("mWebMenu", self.tr("&Web"), self.tr("MetaSearch")),
            ("mMeshMenu", self.tr("&Mesh"), self.tr("Mesh Calculator…")),
            ("processing", self.tr("Pro&cessing"), self.tr("Toolbox")),
        ):
            add_action(self._menu(object_name, title), None, entry)

        help_menu = self._menu("mHelpMenu", self.tr("&Help"))
        add_action(help_menu, "mActionHelpContents", self.tr("Help Contents"))
        add_action(help_menu, None, self.tr("About"))

    # Toolbars --------------------------------------------------------------------------

    def _toolbar(self, object_name: str, title: str) -> QToolBar:
        bar = QToolBar(title, self)
        bar.setObjectName(object_name)
        bar.setIconSize(QSize(24, 24))
        self.addToolBar(bar)
        return bar

    def _build_toolbars(self) -> None:
        file_bar = self._toolbar("mFileToolBar", self.tr("Project Toolbar"))
        for name, text in (
            ("mActionFileNew", self.tr("New Project")),
            ("mActionFileOpen", self.tr("Open Project")),
            ("mActionFileSave", self.tr("Save Project")),
            ("mActionFileSaveAs", self.tr("Save Project As")),
        ):
            add_action(file_bar, name, text)
        file_bar.addSeparator()
        add_action(file_bar, "mActionLayoutManager", self.tr("Layout Manager"))

        nav = self._toolbar("mMapNavToolBar", self.tr("Map Navigation Toolbar"))
        add_action(nav, "mActionPan", self.tr("Pan Map"), checked=True)
        for name, text in (
            ("mActionPanToSelected", self.tr("Pan Map to Selection")),
            ("mActionZoomIn", self.tr("Zoom In")),
            ("mActionZoomOut", self.tr("Zoom Out")),
            ("mActionZoomFullExtent", self.tr("Zoom Full")),
            ("mActionZoomToLayer", self.tr("Zoom to Layer")),
            ("mActionZoomLast", self.tr("Zoom Last")),
            ("mActionZoomNext", self.tr("Zoom Next")),
            ("mActionRefresh", self.tr("Refresh")),
        ):
            add_action(nav, name, text)

        attributes = self._toolbar("mAttributesToolBar", self.tr("Attributes Toolbar"))
        add_action(attributes, "mActionIdentify", self.tr("Identify Features"), checked=False)
        add_action(attributes, "mActionSelectRectangle", self.tr("Select Features"), checked=False)
        add_action(attributes, "mActionDeselectAll", self.tr("Deselect Features"))
        attributes.addSeparator()
        add_action(attributes, "mActionOpenTable", self.tr("Open Attribute Table"))
        add_action(attributes, "mActionCalculateField", self.tr("Open Field Calculator"))
        attributes.addSeparator()
        add_action(attributes, "mActionMeasure", self.tr("Measure Line"), checked=False)
        add_action(attributes, "mActionMapTips", self.tr("Show Map Tips"), checked=False)

        help_bar = self._toolbar("mHelpToolBar", self.tr("Help Toolbar"))
        add_action(help_bar, "mActionHelpContents", self.tr("Help Contents"))

        self.addToolBarBreak()
        sources = self._toolbar("mDataSourceManagerToolBar", self.tr("Data Source Manager Toolbar"))
        for name, text in (
            ("mActionDataSourceManager", self.tr("Open Data Source Manager")),
            ("mActionAddOgrLayer", self.tr("Add Vector Layer")),
            ("mActionAddRasterLayer", self.tr("Add Raster Layer")),
            ("mActionNewGeoPackageLayer", self.tr("New GeoPackage Layer")),
        ):
            add_action(sources, name, text)

        digitize = self._toolbar("mDigitizeToolBar", self.tr("Digitizing Toolbar"))
        add_action(digitize, "mActionToggleEditing", self.tr("Toggle Editing"), checked=False)
        add_action(digitize, "mActionSaveEdits", self.tr("Save Layer Edits"), enabled=False)
        add_action(digitize, "mActionCapturePoint", self.tr("Add Point Feature"), enabled=False)
        add_action(digitize, "mActionVertexTool", self.tr("Vertex Tool"), enabled=False)

    # Central area ----------------------------------------------------------------------

    def _build_central(self) -> None:
        central = QWidget(self)
        central.setObjectName("centralwidget")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        message_bar = QgsMessageBar(central)
        message_bar.pushMessage(
            self.tr("QUI"), self.tr("This is a mockup of QGIS."), Qgis.MessageLevel.Info, 0
        )
        # QUI cannot restyle these (QgsMessageBar sets its own stylesheet; the map is not UI).
        message_bar.setProperty(PICKABLE_PROPERTY, False)
        layout.addWidget(message_bar)
        map_placeholder = MapPlaceholder(central)
        map_placeholder.setProperty(PICKABLE_PROPERTY, False)
        layout.addWidget(map_placeholder, 1)
        self.setCentralWidget(central)

    # Panels ----------------------------------------------------------------------------

    def _dock(self, object_name: str, title: str) -> tuple[QgsDockWidget, QVBoxLayout]:
        dock = QgsDockWidget(title, self)
        dock.setObjectName(object_name)
        contents = QWidget(dock)
        layout = QVBoxLayout(contents)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        dock.setWidget(contents)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        return dock, layout

    def _panel_toolbar(self, layout: QVBoxLayout, object_name: str = "") -> QToolBar:
        bar = QToolBar(layout.parentWidget())
        bar.setObjectName(object_name)
        bar.setIconSize(QSize(16, 16))
        layout.addWidget(bar)
        return bar

    def _build_docks(self) -> None:
        # Browser first: QGIS's default layout stacks Browser above Layers.
        _, layout = self._dock("Browser", self.tr("Browser"))
        bar = self._panel_toolbar(layout, "mBrowserToolbar")
        add_action(bar, "mActionRefresh", self.tr("Refresh"))
        add_action(bar, "mActionAdd", self.tr("Add Selected Layers"))
        add_action(bar, "mActionFilter2", self.tr("Filter Browser"), checked=False)
        add_action(bar, "mActionCollapseTree", self.tr("Collapse All"))
        add_action(bar, "mActionPropertiesWidget", self.tr("Enable/Disable Properties Widget"), checked=False)
        layout.addWidget(self._browser_tree())

        _, layout = self._dock("Layers", self.tr("Layers"))
        bar = self._panel_toolbar(layout)
        add_action(bar, "propertyicons/symbology", self.tr("Open the Layer Styling Panel"))
        add_action(bar, "mActionAddGroup", self.tr("Add Group"))
        add_action(bar, "mActionShowAllLayers", self.tr("Manage Map Themes"))
        add_action(bar, "mActionFilter2", self.tr("Filter Legend"), checked=False)
        add_action(bar, "mActionExpandTree", self.tr("Expand All"))
        add_action(bar, "mActionCollapseTree", self.tr("Collapse All"))
        add_action(bar, "mActionRemoveLayer", self.tr("Remove Layer/Group"))
        layout.addWidget(self._layer_tree())

    def _browser_tree(self) -> QTreeView:
        tree = QTreeView()
        tree.setHeaderHidden(True)
        model = QStandardItemModel(tree)
        entries = (
            ("mIconFavorites", self.tr("Favorites"), ["Projects"]),
            ("mActionShowBookmarks", self.tr("Spatial Bookmarks"), []),
            ("mIconFolderHome", self.tr("Home"), []),
            ("mIconFolder", "C:\\", []),
            ("mActionNewGeoPackageLayer", "GeoPackage", ["world.gpkg"]),
            ("mIconPostgis", "PostgreSQL", []),
            ("mIconWms", "WMS/WMTS", []),
            ("mIconXyz", self.tr("XYZ Tiles"), ["OpenStreetMap"]),
        )
        for icon_name, text, children in entries:
            item = QStandardItem(icon(icon_name), text)
            for child in children:
                item.appendRow(
                    QStandardItem(icon("mIconFolder" if icon_name == "mIconFavorites" else icon_name), child)
                )
            model.appendRow(item)
        tree.setModel(model)
        tree.expandAll()
        tree.setCurrentIndex(model.index(2, 0))
        return tree

    def _layer_tree(self) -> QgsLayerTreeView:
        view = QgsLayerTreeView()
        view.setObjectName("theLayerTreeView")
        # Layers stay out of QgsProject; keep Python references so they live as long as the tree.
        self._layers = [
            QgsVectorLayer(f"{geometry}?crs=EPSG:4326", name, "memory")
            for geometry, name in (
                ("Point", self.tr("Points of interest")),
                ("LineString", self.tr("Roads")),
                ("Polygon", self.tr("Buildings")),
                ("Polygon", self.tr("Land use")),
            )
        ]
        self._layer_root = QgsLayerTree()
        self._layer_root.addLayer(self._layers[0])
        self._layer_root.addLayer(self._layers[1])
        group = self._layer_root.addGroup(self.tr("Base layers"))
        group.addLayer(self._layers[2])
        group.addLayer(self._layers[3]).setItemVisibilityChecked(False)
        view.setModel(QgsLayerTreeModel(self._layer_root, view))
        view.expandAll()
        view.setCurrentLayer(self._layers[1])
        return view

    # Status bar ------------------------------------------------------------------------

    def _build_statusbar(self) -> None:
        status = QStatusBar(self)
        status.setObjectName("statusbar")
        self.setStatusBar(status)

        locator = QLineEdit()
        locator.setPlaceholderText(self.tr("Type to locate (Ctrl+K)"))
        locator.setFixedWidth(220)
        status.addWidget(locator)

        coordinate = QLineEdit("31.2357, 30.0444")
        coordinate.setFixedWidth(130)
        scale = QgsScaleComboBox()
        scale.setScale(25000)
        magnifier = QgsDoubleSpinBox()
        magnifier.setSuffix("%")
        magnifier.setRange(1, 1000)
        magnifier.setValue(100)
        rotation = QgsDoubleSpinBox()
        rotation.setSuffix(" °")
        render = QCheckBox(self.tr("Render"))
        render.setChecked(True)
        crs = QToolButton()
        crs.setIcon(icon("mIconProjectionEnabled"))
        crs.setText("EPSG:4326")
        crs.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        crs.setAutoRaise(True)
        log = QToolButton()
        log.setIcon(icon("mMessageLogRead"))
        log.setAutoRaise(True)
        for widget in (
            QLabel(self.tr("Coordinate")),
            coordinate,
            QLabel(self.tr("Scale")),
            scale,
            QLabel(self.tr("Magnifier")),
            magnifier,
            QLabel(self.tr("Rotation")),
            rotation,
            render,
            crs,
            log,
        ):
            status.addPermanentWidget(widget)


class MapPlaceholder(QWidget):
    """Hand-drawn stand-in for the map canvas (QUI never styles map rendering)."""

    LAND, WATER, PARK, ROAD, ROAD_CASING = "#f2efe9", "#aad3df", "#c8facc", "#ffffff", "#c9c2b5"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("quiMapPlaceholder")
        self.setMinimumSize(200, 150)

    def paintEvent(self, event) -> None:
        w, h = self.width(), self.height()

        def pt(x: float, y: float) -> QPointF:
            return QPointF(x * w, y * h)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(self.LAND))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.WATER))
        painter.drawPolygon(QPolygonF([pt(0.62, 0), pt(1, 0), pt(1, 0.55), pt(0.83, 0.42), pt(0.7, 0.18)]))
        painter.setBrush(QColor(self.PARK))
        painter.drawEllipse(pt(0.18, 0.58), 0.1 * w, 0.12 * h)

        roads = QPainterPath(pt(0, 0.35))
        roads.cubicTo(pt(0.3, 0.3), pt(0.5, 0.55), pt(1, 0.72))
        roads.moveTo(pt(0.42, 1))
        roads.cubicTo(pt(0.45, 0.6), pt(0.38, 0.35), pt(0.5, 0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for color, width in ((self.ROAD_CASING, 9), (self.ROAD, 6)):
            painter.setPen(QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawPath(roads)

        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.setBrush(QColor("#d63d3d"))
        for x, y in ((0.3, 0.42), (0.55, 0.62), (0.47, 0.2)):
            painter.drawEllipse(pt(x, y), 5, 5)
        painter.end()
