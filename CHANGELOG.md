# Changelog

All notable changes to QUI are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- 31 openly licensed community themes, bundled with attribution: QGIS Studio Themes,
  Load QSS, SkinKit (including QDarkStyle, FreeCAD and qmc2 stylesheets) and Tokyo
  Night. They are offered as base themes and in *Presets → Community Themes*.
  `tools/import_themes.py` re-imports them from pinned upstream commits.
- The designed QUI logo is now the plugin icon.

## [0.1.0] - 2026-09-25

### Added

- Clickable QGIS mockup: the main window (menus, toolbars, Layers and Browser
  panels, status bar) and an Options-style dialog. It uses the same Qt classes and
  object names as QGIS, with zoom and a light or dark backdrop.
- Component tree and click-to-select. Clicks on sub-controls such as items, tabs
  and titles select those sub-controls.
- Inspector:
  - per-state background (solid or gradient), text and border colors, border
    width, corner radius and padding,
  - accent-linked colors,
  - live WCAG contrast with a warning below AA.
- Global settings: base QGIS theme, accent color, background opacity, corner
  radius spread and the program font.
- Undo/redo, `.qui.json` save/open and `.qss` export.
- Export as a QGIS UI theme (`style.qss` + `variables.qss`) in the profile.
- Presets: Glass Dark, Glass Light, Minimal and High Contrast, all meeting WCAG AA.
- Apply to QGIS with a 15-second keep/revert confirmation. Restoring the original
  look on demand, on plugin unload and on uninstall gives back the exact original
  stylesheet and font. Optionally, the kept theme is re-applied at start-up.
- English and Turkish user interface.

[Unreleased]: https://github.com/kaanklcrsln/QUI/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kaanklcrsln/QUI/releases/tag/v0.1.0
