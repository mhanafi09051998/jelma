"""Nama berkas hasil: selalu salinan baru di samping berkas asli, tidak pernah menimpa."""
from pathlib import Path


def tujuan(sumber: Path, ext: str, akhiran: str = "") -> Path:
    """`foto.png` + ext `webp` -> `foto.webp`; bila sudah ada -> `foto (1).webp`, dst.

    `akhiran` ditambahkan sebelum ekstensi, mis. akhiran " (kompres)" -> `foto (kompres).jpg`.
    """
    sumber = Path(sumber)
    ext = ext.lstrip(".").lower()
    dasar = sumber.stem + akhiran
    calon = sumber.with_name(f"{dasar}.{ext}")
    n = 1
    while calon.exists():
        calon = sumber.with_name(f"{dasar} ({n}).{ext}")
        n += 1
    return calon


def folder_tujuan(sumber: Path, akhiran: str = "") -> Path:
    """Folder baru di samping berkas, untuk aksi yang menghasilkan banyak berkas (PDF -> PNG per halaman)."""
    sumber = Path(sumber)
    dasar = sumber.stem + akhiran
    calon = sumber.with_name(dasar)
    n = 1
    while calon.exists():
        calon = sumber.with_name(f"{dasar} ({n})")
        n += 1
    calon.mkdir()
    return calon
