"""Utilitas bersama mesin konversi."""
import shutil
import subprocess
import sys
from pathlib import Path


def _akar_aplikasi() -> Path:
    # Saat dibekukan PyInstaller, berkas pendamping ada di samping jelma.exe; saat dev, di akar repo.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


def biner(nama: str) -> str:
    """Path ffmpeg/ffprobe: vendor/ bawaan dulu, lalu PATH."""
    for calon in (_akar_aplikasi() / "vendor" / f"{nama}.exe", _akar_aplikasi() / f"{nama}.exe"):
        if calon.exists():
            return str(calon)
    dari_path = shutil.which(nama)
    if not dari_path:
        raise RuntimeError(f"{nama} tidak ditemukan")
    return dari_path


TANPA_JENDELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
