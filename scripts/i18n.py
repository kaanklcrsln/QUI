"""Translations: extract strings into qui/i18n/*.ts and compile them to .qm.

    scripts\\dev.bat python scripts\\i18n.py update    # pylupdate5; keeps existing translations
    scripts\\dev.bat python scripts\\i18n.py compile   # .ts -> .qm (pure Python, no lrelease)

Translate the .ts files with Qt Linguist or any text editor, then run "compile".
To add a language, copy qui_tr.ts to qui_<code>.ts, clear the translations, translate.
"""

from __future__ import annotations

import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "qui"
I18N = PLUGIN / "i18n"

# QTranslator's .qm format (qtranslator.cpp / releaser.cpp in Qt's linguist).
QM_MAGIC = bytes.fromhex("3cb86418caef9c95cd211cbf60a1bddd")
TAG_HASHES, TAG_MESSAGES = 0x42, 0x69
TAG_END, TAG_TRANSLATION, TAG_SOURCE, TAG_CONTEXT, TAG_COMMENT = 1, 3, 6, 7, 8


def elf_hash(data: bytes) -> int:
    """Qt's elfHash() over source text + comment, used as the lookup key."""
    h = 0
    for byte in data:
        h = ((h << 4) + byte) & 0xFFFFFFFF
        g = h & 0xF0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xFFFFFFFF
    return h or 1


def _bytes_field(tag: int, data: bytes) -> bytes:
    return struct.pack(">BI", tag, len(data)) + data


def compile_ts(ts: Path, qm: Path) -> int:
    """Write *qm* from the finished translations in *ts*; returns how many were written."""
    messages, hashes = bytearray(), []
    for context in ET.parse(ts).getroot().iter("context"):
        context_name = (context.findtext("name") or "").encode("utf-8")
        for message in context.iter("message"):
            translation = message.find("translation")
            if translation is None or translation.get("type") in ("unfinished", "vanished", "obsolete"):
                continue
            if not translation.text:
                continue
            source = (message.findtext("source") or "").encode("utf-8")
            comment = (message.findtext("comment") or "").encode("utf-8")
            hashes.append((elf_hash(source + comment), len(messages)))
            messages += _bytes_field(TAG_TRANSLATION, translation.text.encode("utf-16-be"))
            messages += _bytes_field(TAG_SOURCE, source)
            messages += _bytes_field(TAG_CONTEXT, context_name)
            messages += _bytes_field(TAG_COMMENT, comment)
            messages.append(TAG_END)
    hash_table = b"".join(struct.pack(">II", h, offset) for h, offset in sorted(hashes))
    qm.write_bytes(
        QM_MAGIC + _bytes_field(TAG_HASHES, hash_table) + _bytes_field(TAG_MESSAGES, bytes(messages))
    )
    return len(hashes)


def update() -> None:
    sources = sorted(str(p.relative_to(ROOT)) for p in PLUGIN.rglob("*.py"))
    for ts in sorted(I18N.glob("qui_*.ts")):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "PyQt5.pylupdate_main",
                "-noobsolete",
                *sources,
                "-ts",
                str(ts.relative_to(ROOT)),
            ],
            cwd=ROOT,
            check=True,
        )
        print(f"updated {ts.name}")


def compile_all() -> None:
    for ts in sorted(I18N.glob("qui_*.ts")):
        count = compile_ts(ts, ts.with_suffix(".qm"))
        print(f"compiled {ts.with_suffix('.qm').name}: {count} translations")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "update":
        update()
    elif command == "compile":
        compile_all()
    else:
        sys.exit(__doc__)
