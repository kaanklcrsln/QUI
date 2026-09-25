"""Run the QUI editor outside QGIS for quick iteration.

Usage (Windows)::

    scripts\\dev.bat python scripts\\run_standalone.py

Starts a bare QgsApplication (no QGIS main window, no iface) and opens the editor.
Note: QGIS's main-window stylesheet does not cascade here, unlike inside QGIS.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qgis.core import QgsApplication  # noqa: E402

from qui.gui.editor_window import EditorWindow  # noqa: E402


def main() -> int:
    app = QgsApplication([], True)
    app.initQgis()
    window = EditorWindow()
    window.show()
    code = app.exec()
    app.exitQgis()
    return code


if __name__ == "__main__":
    sys.exit(main())
