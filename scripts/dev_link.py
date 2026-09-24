"""Link the ``qui/`` plugin folder into a QGIS profile for live development.

Usage::

    python scripts/dev_link.py              # link into the "default" profile
    python scripts/dev_link.py --unlink     # remove the link (never touches qui/)
    python scripts/dev_link.py --profile work --profiles-dir <path>

Windows gets a directory junction (no admin rights needed), other platforms a symlink.
After linking, restart QGIS once and enable QUI in the Plugin Manager; from then on
Plugin Reloader picks up code changes.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "qui"


def default_profiles_dir() -> Path:
    """Standard QGIS 3 profiles location for the current platform."""
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / "QGIS" / "QGIS3" / "profiles"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "QGIS" / "QGIS3" / "profiles"
    return Path.home() / ".local" / "share" / "QGIS" / "QGIS3" / "profiles"


def is_link(path: Path) -> bool:
    """True for symlinks and Windows junctions."""
    try:
        os.readlink(path)
        return True
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", default="default")
    parser.add_argument("--profiles-dir", type=Path, default=default_profiles_dir())
    parser.add_argument("--unlink", action="store_true")
    args = parser.parse_args()

    plugins_dir = args.profiles_dir / args.profile / "python" / "plugins"
    link = plugins_dir / SOURCE.name

    if args.unlink:
        if not is_link(link):
            print(f"Nothing to unlink: {link} is not a link.")
            return 1
        if sys.platform == "win32":
            os.rmdir(link)  # removes the junction only, not its target
        else:
            link.unlink()
        print(f"Removed link {link}")
        return 0

    if link.exists() or is_link(link):
        if is_link(link) and link.exists() and os.path.samefile(link, SOURCE):
            print(f"Already linked: {link} -> {SOURCE}")
            return 0
        print(f"Refusing to overwrite existing {link}; remove it first.")
        return 1

    plugins_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(SOURCE)], check=True)
    else:
        link.symlink_to(SOURCE, target_is_directory=True)
    print(f"Linked {link} -> {SOURCE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
