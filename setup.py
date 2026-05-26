"""Build the portable Cashy distribution via PyInstaller."""
import subprocess
import sys

subprocess.run(
    [sys.executable, "-m", "PyInstaller", "cashy.spec", "--noconfirm", "--clean"],
    check=True,
)
