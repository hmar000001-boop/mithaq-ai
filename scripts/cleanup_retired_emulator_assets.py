#!/usr/bin/env python3
"""Remove exact legacy emulator/E2E paths left by ZIP-overlay updates.

Extracting a new project ZIP over an existing Git checkout overwrites files
that are present in the archive but does not delete older tracked files omitted
from it. This allowlisted cleanup runs immediately after checkout and before
all project invariants, so retired instrumentation sources cannot survive into
host-only CI builds.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
RETIRED_PATHS = (
    Path("app/src/androidTest"),
    Path("unauthorized-probe"),
    Path("scripts/run_emulator_boundary_tests.sh"),
    Path("scripts/test_emulator_boundary_runner.py"),
)


def remove_path(path: Path, root: Path) -> bool:
    """Remove a file, directory or final-component symlink without following it."""
    root = root.resolve()
    candidate = root / path
    if not candidate.is_relative_to(root):
        raise ValueError(f"Refusing cleanup path outside project root: {path}")

    # Do not traverse a symlinked parent: it could redirect deletion outside the checkout.
    for parent in candidate.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError(f"Refusing cleanup through symlinked parent: {parent}")

    if candidate.is_symlink() or candidate.is_file():
        candidate.unlink()
        return True
    if candidate.is_dir():
        shutil.rmtree(candidate)
        return True
    return False


def cleanup_retired_assets(root: Path = ROOT) -> list[str]:
    removed: list[str] = []
    for relative in RETIRED_PATHS:
        if remove_path(relative, root):
            removed.append(relative.as_posix())
    return removed


def main() -> int:
    removed = cleanup_retired_assets(ROOT)
    if removed:
        print("Removed legacy emulator/E2E assets from this checkout:")
        for item in removed:
            print(f"- {item}")
    else:
        print("Legacy emulator/E2E cleanup: no stale assets found")
    print("Legacy emulator/E2E cleanup: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
