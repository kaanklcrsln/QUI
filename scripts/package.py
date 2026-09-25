"""Build the release zip for plugins.qgis.org and the custom plugin repository.

    python scripts/package.py                      # -> dist/qui-<version>.zip
    python scripts/package.py --plugins-xml        # also rewrite repository/plugins.xml

Validates metadata.txt, compiles translations (.ts -> .qm) and zips the ``qui/``
folder as the single root, without caches, hidden files or translation sources.
Needs only the Python standard library (no QGIS, no Qt tools).
"""

from __future__ import annotations

import argparse
import configparser
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "qui"
DIST = ROOT / "dist"
PLUGINS_XML = ROOT / "repository" / "plugins.xml"
REPO = "kaanklcrsln/QUI"

sys.path.insert(0, str(ROOT / "tools"))
import i18n  # noqa: E402

REQUIRED = (
    "name", "qgisMinimumVersion", "supportsQt6", "description", "about", "version", "author",
    "email", "repository", "tracker", "homepage", "tags", "category", "icon", "experimental", "changelog",
)  # fmt: skip
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".ts"}


def read_metadata() -> configparser.SectionProxy:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(PLUGIN / "metadata.txt", encoding="utf-8")
    return parser["general"]


def validate(meta: configparser.SectionProxy) -> None:
    """The checks plugins.qgis.org runs on upload that we can run offline."""
    problems = [
        f"metadata.txt: '{key}' is missing or empty" for key in REQUIRED if not meta.get(key, "").strip()
    ]
    if not re.fullmatch(r"\d+\.\d+\.\d+([-.]\w+)?", meta.get("version", "")):
        problems.append(f"metadata.txt: version {meta.get('version')!r} is not like 1.2.3")
    for required_file in ("LICENSE", meta.get("icon", "")):
        if not (PLUGIN / required_file).is_file():
            problems.append(f"qui/{required_file} is missing")
    if problems:
        sys.exit("\n".join(problems))


def included(path: Path) -> bool:
    parts = path.relative_to(PLUGIN).parts
    return (
        path.is_file()
        and not any(part.startswith(".") or part == "__pycache__" for part in parts)
        and path.suffix not in EXCLUDED_SUFFIXES
    )


def build_zip(version: str) -> Path:
    i18n.compile_all()
    DIST.mkdir(exist_ok=True)
    target = DIST / f"qui-{version}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PLUGIN.rglob("*")):
            if included(path):
                archive.write(path, Path("qui") / path.relative_to(PLUGIN))
    return target


def write_plugins_xml(meta: configparser.SectionProxy, zip_name: str) -> None:
    """A QGIS plugin repository listing this release (Plugin Manager > Settings > Add)."""
    version = meta["version"]
    raw = f"https://raw.githubusercontent.com/{REPO}/main"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fields = {
        "description": meta["description"],
        "about": meta["about"],
        "version": version,
        "qgis_minimum_version": meta["qgisMinimumVersion"],
        "qgis_maximum_version": meta.get("qgisMaximumVersion", "3.99"),
        "supports_qt6": meta["supportsQt6"],
        "homepage": meta["homepage"],
        # QGIS derives the plugin id from file_name up to the first dot, so it must be
        # "qui.<version>.zip" whatever the downloaded file is called.
        "file_name": f"{PLUGIN.name}.{version}.zip",
        "icon": f"{raw}/qui/{meta['icon']}",
        "author_name": meta["author"],
        "download_url": f"https://github.com/{REPO}/releases/download/v{version}/{zip_name}",
        "uploaded_by": meta["author"],
        "create_date": today,
        "update_date": today,
        "experimental": meta["experimental"],
        "deprecated": meta.get("deprecated", "False"),
        "tracker": meta["tracker"],
        "repository": meta["repository"],
        "tags": meta["tags"],
        "server": meta.get("server", "False"),
    }
    body = "\n".join(f"    <{key}>{escape(value)}</{key}>" for key, value in fields.items())
    PLUGINS_XML.parent.mkdir(exist_ok=True)
    with open(PLUGINS_XML, "w", encoding="utf-8", newline="\n") as file:
        file.write(
            '<?xml version="1.0" encoding="UTF-8"?>\n<plugins>\n'
            f'  <pyqgis_plugin name="{escape(meta["name"])}" version="{version}">\n{body}\n'
            "  </pyqgis_plugin>\n</plugins>\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plugins-xml", action="store_true", help="also rewrite repository/plugins.xml")
    args = parser.parse_args()
    meta = read_metadata()
    validate(meta)
    target = build_zip(meta["version"])
    print(f"built {target.relative_to(ROOT)} ({target.stat().st_size // 1024} KiB)")
    if args.plugins_xml:
        write_plugins_xml(meta, target.name)
        print(f"wrote {PLUGINS_XML.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
