"""Qt5/Qt6 differences that ``qgis.PyQt`` does not paper over."""

try:  # Qt6 moved these from QtWidgets to QtGui
    from qgis.PyQt.QtGui import QAction, QUndoCommand, QUndoStack
except ImportError:
    from qgis.PyQt.QtWidgets import QAction, QUndoCommand, QUndoStack

__all__ = ["QAction", "QUndoCommand", "QUndoStack"]
