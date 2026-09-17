#!/usr/bin/env python3
"""Copy or verify a complete Noah-MP working tree for offline SCM peer tests.

Run this on Linux/WSL so Git-tracked symbolic links remain symbolic links.
No Git history is copied and no commits are created.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import os
from pathlib import Path
import shutil
import subprocess


SCM_ROOT = Path(__file__).resolve().parents[2]
VENDOR_ROOT = (
    SCM_ROOT
    / "ccpp"
    / "physics"
    / "physics"
    / "SFC_Models"
    / "Land"
    / "NoahmpModular"
    / "noahmp"
)
OLD_MANIFEST = VENDOR_ROOT / "VENDORED_MANIFEST.sha256"


def source_files(source_root: Path) -> list[Path]:
    """Select community-tracked files plus the uncommitted CCPP driver."""
    index = subprocess.check_output(
        ["git", "ls-files", "--stage", "-z"], cwd=source_root
    )
    paths = set()
    for entry in index.split(b"\0"):
        if not entry:
            continue
        info, name = entry.split(b"\t", 1)
        relative = Path(os.fsdecode(name))
        if info.split()[0] == b"120000" and not (source_root / relative).is_symlink():
            raise RuntimeError(
                f"Git symlink {relative} is not a symlink in the source checkout; "
                "run this script on Linux/WSL"
            )
        paths.add(relative)

    ccpp_driver = source_root / "drivers" / "ccpp"
    if not (ccpp_driver / "noahmp.F90").is_file():
        raise RuntimeError(f"Missing modular CCPP driver: {ccpp_driver / 'noahmp.F90'}")
    for path in ccpp_driver.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            paths.add(path.relative_to(source_root))
    return sorted(paths)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def matches(source: Path, destination: Path) -> bool:
    if source.is_symlink():
        return destination.is_symlink() and os.readlink(source) == os.readlink(destination)
    return destination.is_file() and not destination.is_symlink() and digest(source) == digest(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=SCM_ROOT.parent / "noahmp",
        help="modular Noah-MP checkout (default: sibling noahmp directory)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="verify the complete copied tree without changing files",
    )
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    if os.name == "nt":
        raise SystemExit("Run this script on Linux/WSL to preserve Noah-MP symlinks")
    if source_root == VENDOR_ROOT.resolve():
        raise SystemExit("Source and destination cannot be the same directory")

    relative_files = source_files(source_root)
    expected = set(relative_files)
    actual = {
        path.relative_to(VENDOR_ROOT)
        for path in VENDOR_ROOT.rglob("*")
        if (path.is_file() or path.is_symlink())
        and "__pycache__" not in path.parts and path.suffix != ".pyc"
    } - {OLD_MANIFEST.relative_to(VENDOR_ROOT)}
    extra = sorted(actual - expected)
    if extra:
        for relative in extra:
            print(f"Unexpected file: {relative.as_posix()}")
        raise SystemExit(1)

    if args.check:
        missing = sorted(expected - actual)
        changed = sorted(
            relative for relative in expected & actual
            if not matches(source_root / relative, VENDOR_ROOT / relative)
        )
        if missing or changed or OLD_MANIFEST.exists():
            for label, paths in (("Missing", missing), ("Changed", changed)):
                for path in paths:
                    print(f"{label}: {path.as_posix()}")
            if OLD_MANIFEST.exists():
                print("Old dependency-closure manifest remains in the copy")
            raise SystemExit(1)
        print(f"Verified complete Noah-MP working tree ({len(relative_files)} files) in {VENDOR_ROOT}")
        return

    for relative in relative_files:
        source = source_root / relative
        destination = VENDOR_ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if matches(source, destination):
            continue
        if destination.exists() or destination.is_symlink():
            destination.unlink()
        if source.is_symlink():
            destination.symlink_to(os.readlink(source))
        else:
            shutil.copy2(source, destination)

    if OLD_MANIFEST.exists():
        OLD_MANIFEST.unlink()
    print(f"Copied complete Noah-MP working tree ({len(relative_files)} files) to {VENDOR_ROOT}")


if __name__ == "__main__":
    main()
