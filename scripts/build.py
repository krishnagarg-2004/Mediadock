"""Build orchestration script for packaging MediaDock into a standalone Windows executable."""

import sys
import os
import shutil
import subprocess
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SPEC_FILE = os.path.join(PROJECT_ROOT, "MediaDock.spec")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
EXE_PATH = os.path.join(DIST_DIR, "MediaDock.exe")


def clean_stale_build_output() -> None:
    """Clean previous build/ and dist/ output directories."""
    print("--- Cleaning Stale Build Outputs ---")
    for directory in (BUILD_DIR, DIST_DIR):
        if os.path.exists(directory):
            print(f"Removing directory: {directory}")
            shutil.rmtree(directory, ignore_errors=True)
    print("Clean completed.\n")


def run_pyinstaller_build() -> None:
    """Invoke PyInstaller using MediaDock.spec."""
    print("--- Invoking PyInstaller Build ---")
    if not os.path.exists(SPEC_FILE):
        print(f"ERROR: Spec file missing at {SPEC_FILE}", file=sys.stderr)
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        SPEC_FILE,
        "--noconfirm",
        "--clean",
    ]

    print(f"Running command: {' '.join(cmd)}")
    start_time = time.time()
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.time() - start_time

    if result.returncode != 0:
        print(f"\nERROR: PyInstaller build failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)

    print(f"PyInstaller build succeeded in {elapsed:.2f} seconds.\n")


def verify_executable_output() -> None:
    """Verify that dist/MediaDock.exe exists and is non-zero size."""
    print("--- Verifying Build Artifact ---")
    if not os.path.exists(EXE_PATH):
        print(f"ERROR: Executable artifact missing at expected path: {EXE_PATH}", file=sys.stderr)
        sys.exit(1)

    size_bytes = os.path.getsize(EXE_PATH)
    if size_bytes == 0:
        print(f"ERROR: Executable artifact is 0 bytes: {EXE_PATH}", file=sys.stderr)
        sys.exit(1)

    size_mb = size_bytes / (1024 * 1024)
    print(f"SUCCESS: Executable created successfully!")
    print(f"  Path: {EXE_PATH}")
    print(f"  Size: {size_bytes:,} bytes ({size_mb:.2f} MB)")
    print("--------------------------------\n")


def main() -> None:
    """Main build entry point."""
    print("==========================================")
    print("  MediaDock Packaging & Build Pipeline    ")
    print("==========================================\n")
    clean_stale_build_output()
    run_pyinstaller_build()
    verify_executable_output()


if __name__ == "__main__":
    main()
