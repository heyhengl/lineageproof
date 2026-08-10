#!/usr/bin/env python3
"""Build a deterministic, dependency-free LineageProof scanner zipapp."""

import argparse
from pathlib import Path

from lineageproof.zipapp_build import build_merchant_scan_zipapp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("src"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_merchant_scan_zipapp(args.source_root, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
