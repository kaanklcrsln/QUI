"""QUI - Quantum User Interfaces: a visual theme editor for the QGIS user interface."""


def classFactory(iface):
    """QGIS entry point: return the plugin instance."""
    from .plugin import QuiPlugin

    return QuiPlugin(iface)
