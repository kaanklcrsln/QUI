"""Upload a release zip to plugins.qgis.org through its XML-RPC API.

    OSGEO_USERNAME=... OSGEO_PASSWORD=... python scripts/upload_plugin.py dist/qui-0.1.0.zip

The first version of a new plugin still waits for approval by the plugins.qgis.org
staff; later versions of an approved plugin are published right away.
"""

from __future__ import annotations

import os
import sys
import xmlrpc.client
from pathlib import Path
from urllib.parse import quote

ENDPOINT = "plugins.qgis.org/plugins/RPC2/"


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    user, password = os.environ.get("OSGEO_USERNAME"), os.environ.get("OSGEO_PASSWORD")
    if not user or not password:
        sys.exit("Set OSGEO_USERNAME and OSGEO_PASSWORD (your OSGeo ID).")
    server = xmlrpc.client.ServerProxy(
        f"https://{quote(user, safe='')}:{quote(password, safe='')}@{ENDPOINT}"
    )
    data = xmlrpc.client.Binary(Path(sys.argv[1]).read_bytes())
    try:
        plugin_id, version_id = server.plugin.upload(data)
    except xmlrpc.client.Fault as fault:
        sys.exit(f"plugins.qgis.org refused the upload: {fault.faultString}")
    except xmlrpc.client.ProtocolError as error:
        sys.exit(f"plugins.qgis.org error {error.errcode}: {error.errmsg}")
    print(f"Uploaded: plugin id {plugin_id}, version id {version_id}")


if __name__ == "__main__":
    main()
