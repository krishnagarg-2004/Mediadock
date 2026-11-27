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


def compile_inno_setup_installer() -> None:
    """Compile Inno Setup Windows installer if ISCC.exe is available."""
    iss_file = os.path.join(PROJECT_ROOT, "installer", "installer.iss")
    if not os.path.exists(iss_file):
        return

    # Look for Inno Setup compiler in PATH or standard installation directory
    iscc_path = shutil.which("ISCC.exe") or shutil.which("iscc")
    if not iscc_path:
        default_paths = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"),
            os.path.expandvars(r"%ProgramFiles%\Inno Setup 6\ISCC.exe"),
            os.path.expandvars(r"%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"),
        ]
        for p in default_paths:
            if os.path.isfile(p):
                iscc_path = p
                break

    if not iscc_path:
        print("NOTE: Inno Setup (ISCC.exe) not found; skipping MediaDock-Setup.exe installer generation.")
        print("      (To build the installer, install Inno Setup 6 from https://jrsoftware.org/isdl.php)\n")
        return

    print("--- Compiling Windows Installer with Inno Setup ---")
    cmd = [iscc_path, iss_file]
    result = subprocess.run(cmd, cwd=os.path.dirname(iss_file))
    if result.returncode == 0:
        setup_exe = os.path.join(DIST_DIR, "MediaDock-Setup.exe")
        if os.path.exists(setup_exe):
            size_mb = os.path.getsize(setup_exe) / (1024 * 1024)
            print(f"SUCCESS: Installer generated at {setup_exe} ({size_mb:.2f} MB)\n")
    else:
        print(f"WARNING: Inno Setup compilation exited with code {result.returncode}\n")


def main() -> None:
    """Main build entry point."""
    print("==========================================")
    print("  MediaDock Packaging & Build Pipeline    ")
    print("==========================================\n")
    clean_stale_build_output()
    run_pyinstaller_build()
    verify_executable_output()
    compile_inno_setup_installer()


if __name__ == "__main__":
    main()
