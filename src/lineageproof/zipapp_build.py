"""Deterministic zipapp builder for the credential-free Merchant scanner."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ZIPAPP_MAIN = b"from lineageproof.cli import main\nraise SystemExit(main())\n"


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def build_merchant_scan_zipapp(source_root: Path, output: Path) -> None:
    """Package LineageProof into a byte-for-byte deterministic Python zipapp."""

    source_root = source_root.resolve()
    package_root = source_root / "lineageproof"
    if not (package_root / "merchant_scan.py").is_file():
        raise ValueError(f"LineageProof package not found below: {source_root}")

    entries = {
        path.relative_to(source_root).as_posix(): path.read_bytes()
        for path in sorted(package_root.glob("*.py"))
    }
    entries["__main__.py"] = ZIPAPP_MAIN

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        with zipfile.ZipFile(
            temporary,
            mode="x",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for name in sorted(entries):
                archive.writestr(_zip_info(name), entries[name])
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
