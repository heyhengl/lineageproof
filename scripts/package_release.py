#!/usr/bin/env python3
"""Build and verify a deterministic, privacy-scoped source release archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath

ROOT_FILES = (
    ".gitignore",
    ".python-version",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "pyproject.toml",
    "uv.lock",
)

PUBLIC_GLOBS = (
    "docs/*.md",
    "examples/*.json",
    "examples/expected-output/*",
    "scripts/*.py",
    "scripts/*.swift",
    "src/lineageproof/*.py",
    "submission/*.md",
    "tests/*.py",
)

FORBIDDEN_PARTS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "design",
    "dist",
}

ARCHIVE_NAME = "lineageproof-0.1.0-source.zip"
MANIFEST_NAME = "lineageproof-0.1.0-source-manifest.json"
ZIP_TIMESTAMP = (2026, 7, 18, 0, 0, 0)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def collect_public_files(root: Path) -> list[Path]:
    candidates = [root / name for name in ROOT_FILES]
    for pattern in PUBLIC_GLOBS:
        candidates.extend(root.glob(pattern))

    missing = [str(path.relative_to(root)) for path in candidates if not path.exists()]
    if missing:
        raise FileNotFoundError(f"release inputs missing: {missing}")

    files: list[Path] = []
    for path in sorted(set(candidates)):
        relative = path.relative_to(root)
        if path.is_symlink():
            raise ValueError(f"release input must not be a symlink: {relative}")
        if not path.is_file():
            continue
        if FORBIDDEN_PARTS.intersection(relative.parts):
            raise ValueError(f"forbidden release path: {relative}")
        files.append(path)
    return files


def build_release(root: Path, output_dir: Path) -> tuple[Path, Path, dict[str, object]]:
    files = collect_public_files(root)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / ARCHIVE_NAME
    manifest_path = output_dir / MANIFEST_NAME

    entries: list[dict[str, object]] = []
    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
            info = zipfile.ZipInfo(relative, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, data, compresslevel=9)
            entries.append({"path": relative, "bytes": len(data), "sha256": sha256(data)})

    manifest: dict[str, object] = {
        "schema_version": 1,
        "project": "LineageProof",
        "version": "0.1.0",
        "archive": ARCHIVE_NAME,
        "archive_bytes": archive_path.stat().st_size,
        "archive_sha256": sha256(archive_path.read_bytes()),
        "file_count": len(entries),
        "files": entries,
        "scope": {
            "included": list(ROOT_FILES) + list(PUBLIC_GLOBS),
            "forbidden_path_parts": sorted(FORBIDDEN_PARTS),
            "design_assets_included": False,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    verify_release_archive(archive_path, manifest)
    return archive_path, manifest_path, manifest


def verify_release_archive(archive_path: Path, manifest: dict[str, object]) -> None:
    entries = manifest["files"]
    if not isinstance(entries, list):
        raise AssertionError("manifest files must be a list")
    expected_entries = {entry["path"]: entry for entry in entries if isinstance(entry, dict)}
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise AssertionError("release archive contains duplicate paths")
        if set(names) != set(expected_entries):
            raise AssertionError("release archive contents differ from manifest")

        for name in names:
            pure_path = PurePosixPath(name)
            if pure_path.is_absolute() or ".." in pure_path.parts:
                raise AssertionError(f"unsafe archive path: {name}")
            if FORBIDDEN_PARTS.intersection(pure_path.parts):
                raise AssertionError(f"forbidden path packaged: {name}")
            data = archive.read(name)
            expected = expected_entries[name]
            if sha256(data) != expected["sha256"] or len(data) != expected["bytes"]:
                raise AssertionError(f"archive digest mismatch: {name}")

    if sha256(archive_path.read_bytes()) != manifest["archive_sha256"]:
        raise AssertionError("archive digest mismatch")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("dist/release"),
        help="directory for the archive and manifest",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    archive_path, manifest_path, manifest = build_release(root, args.out.resolve())
    print(
        json.dumps(
            {
                "archive": str(archive_path),
                "archive_sha256": manifest["archive_sha256"],
                "design_assets_included": False,
                "file_count": manifest["file_count"],
                "manifest": str(manifest_path),
                "status": "pass",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
