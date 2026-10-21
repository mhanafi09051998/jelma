"""Katalog aksi: sumber tunggal untuk menu klik kanan, menu pintasan, dan CLI.

Setiap aksi menunjuk fungsi mesin `modul:fungsi` dengan kontrak:
    fungsi(sumber: Path, lapor: Callable[[float], None], **opsi) -> list[Path]
`lapor(0.0..1.0)` untuk progres; kembalikan daftar berkas hasil (dibuat lewat `keluaran`).
"""
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path

GAMBAR = ("png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", "ico", "heic", "heif", "avif")
VIDEO = ("mp4", "mkv", "webm", "mov", "avi", "m4v", "wmv", "flv")
AUDIO = ("mp3", "wav", "ogg", "flac", "m4a", "aac", "opus", "wma")
PDF = ("pdf",)

KELOMPOK = {"gambar": GAMBAR, "video": VIDEO, "audio": AUDIO, "pdf": PDF}


@dataclass(frozen=True)
class Aksi:
    id: str          # dipakai di CLI & registri, mis. "gambar-ke-webp"
    label: str       # teks menu
    fungsi: str      # "jelma.mesin.gambar:ke_format"
    opsi: dict = field(default_factory=dict)
    format_tujuan: str = ""  # bila diisi, aksi disembunyikan untuk sumber berformat sama
    pemisah: bool = False    # garis pemisah sebelum item ini di menu


def _format(kel: str, fmt: str, fungsi: str) -> Aksi:
    return Aksi(f"{kel}-ke-{fmt}", f"Ke {fmt.upper()}", fungsi, {"format": fmt}, format_tujuan=fmt)


_G = "jelma.mesin.gambar"
_M = "jelma.mesin.media"
_P = "jelma.mesin.pdf"
_A = "jelma.mesin.alat"

AKSI_PER_KELOMPOK: dict[str, list[Aksi]] = {
    "gambar": [
        *[_format("gambar", f, f"{_G}:ke_format") for f in ("png", "jpg", "webp", "avif", "bmp", "gif", "tiff", "ico")],
        Aksi("gambar-ke-pdf", "Ke PDF", f"{_P}:gambar_ke_pdf", pemisah=True),
        Aksi("gambar-kompres", "Kompres", f"{_G}:kompres", pemisah=True),
        Aksi("gambar-perkecil-50", "Perkecil 50%", f"{_G}:ubah_ukuran", {"skala": 0.5}),
        Aksi("gambar-hapus-metadata", "Hapus metadata (GPS, kamera)", f"{_A}:hapus_metadata"),
        Aksi("gambar-baca-qr", "Baca QR code", f"{_A}:baca_qr"),
    ],
    "video": [
        *[_format("video", f, f"{_M}:video_ke_format") for f in ("mp4", "mkv", "webm", "mov")],
        Aksi("video-ke-gif", "Ke GIF", f"{_M}:video_ke_gif", pemisah=True),
        Aksi("video-ambil-mp3", "Ambil audio (MP3)", f"{_M}:ambil_audio", {"format": "mp3"}),
        Aksi("video-kompres", "Kompres", f"{_M}:kompres_video", pemisah=True),
        Aksi("video-hapus-metadata", "Hapus metadata", f"{_A}:hapus_metadata"),
    ],
    "audio": [
        *[_format("audio", f, f"{_M}:audio_ke_format") for f in ("mp3", "wav", "ogg", "flac", "m4a", "opus")],
        Aksi("audio-hapus-metadata", "Hapus metadata", f"{_A}:hapus_metadata", pemisah=True),
    ],
    "pdf": [
        Aksi("pdf-kompres", "Kompres PDF", f"{_P}:kompres"),
        Aksi("pdf-ke-png", "Ke PNG (per halaman)", f"{_P}:ke_gambar", {"format": "png"}),
        Aksi("pdf-ke-jpg", "Ke JPG (per halaman)", f"{_P}:ke_gambar", {"format": "jpg"}),
        Aksi("pdf-hapus-metadata", "Hapus metadata", f"{_A}:hapus_metadata", pemisah=True),
    ],
}

SEMUA: dict[str, Aksi] = {a.id: a for daftar in AKSI_PER_KELOMPOK.values() for a in daftar}


def kelompok_dari(path: Path | str) -> str | None:
    ext = Path(path).suffix.lstrip(".").lower()
    return next((k for k, exts in KELOMPOK.items() if ext in exts), None)


def aksi_untuk(path: Path | str) -> list[Aksi]:
    """Aksi yang relevan untuk satu berkas; format tujuan yang sama dengan sumber disembunyikan."""
    kel = kelompok_dari(path)
    if not kel:
        return []
    ext = Path(path).suffix.lstrip(".").lower()
    sama = {"jpeg": "jpg", "tif": "tiff", "heif": "heic"}.get(ext, ext)
    return [a for a in AKSI_PER_KELOMPOK[kel] if a.format_tujuan != sama]


def aksi_bersama(paths: list[Path]) -> list[Aksi]:
    """Untuk banyak berkas terpilih: hanya aksi yang berlaku untuk semuanya (dipakai menu pintasan)."""
    if not paths:
        return []
    id_bersama = set.intersection(*({a.id for a in aksi_untuk(p)} for p in paths))
    return [a for a in aksi_untuk(paths[0]) if a.id in id_bersama]


def jalankan(aksi_id: str, sumber: Path, lapor=lambda _p: None) -> list[Path]:
    aksi = SEMUA[aksi_id]
    modul, nama = aksi.fungsi.split(":")
    fungsi = getattr(import_module(modul), nama)
    return fungsi(Path(sumber), lapor, **aksi.opsi)
