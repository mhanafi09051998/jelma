"""Alat lintas jenis berkas: hapus metadata dan baca QR code."""
import subprocess
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps

from jelma import keluaran
from jelma.daftar_aksi import kelompok_dari
from jelma.mesin import TANPA_JENDELA, biner

_AKHIRAN = " (tanpa metadata)"
_FORMAT_PIL = {
    "jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP", "bmp": "BMP", "gif": "GIF",
    "tiff": "TIFF", "tif": "TIFF", "ico": "ICO", "avif": "AVIF", "heic": "HEIF", "heif": "HEIF",
}


def _daftarkan_heif() -> None:
    import pillow_heif
    pillow_heif.register_heif_opener()


def _bingkai_bersih(img: Image.Image) -> list[Image.Image]:
    """Salinan piksel tiap bingkai, tanpa info/EXIF/XMP bawaan berkas asli."""
    jumlah = getattr(img, "n_frames", 1)
    bingkai = []
    for i in range(jumlah):
        img.seek(i)
        salinan = img.copy()
        salinan.info = {}
        bingkai.append(salinan)
    return bingkai


def _simpan_gambar(img: Image.Image, hasil: Path, ext: str) -> None:
    fmt = _FORMAT_PIL[ext]
    icc = img.info.get("icc_profile")
    opsi: dict = {"icc_profile": icc} if icc and fmt not in ("GIF", "BMP", "ICO") else {}
    orientasi = img.getexif().get(0x0112, 1)

    if fmt == "JPEG" and img.format == "JPEG" and orientasi == 1:
        # Tanpa rotasi: pakai ulang tabel kuantisasi asli agar mutu tidak turun.
        img.info = {}
        img.save(hasil, "JPEG", quality="keep", subsampling="keep", qtables="keep", **opsi)
        return

    if orientasi != 1:
        img.seek(0)
        bingkai = [ImageOps.exif_transpose(img)]
        bingkai[0].info = {}
    else:
        bingkai = _bingkai_bersih(img)
    if fmt == "JPEG":
        opsi.update(quality=95, subsampling=0)
        if bingkai[0].mode not in ("RGB", "L", "CMYK"):
            bingkai[0] = bingkai[0].convert("RGB")
    elif fmt in ("WEBP", "AVIF", "HEIF"):
        opsi.update(quality=95)
    if "transparency" in img.info and fmt in ("PNG", "GIF"):
        opsi["transparency"] = img.info["transparency"]
    if len(bingkai) > 1 and fmt in ("GIF", "WEBP", "TIFF", "AVIF"):
        for kunci in ("duration", "loop", "disposal"):
            if kunci in img.info:
                opsi[kunci] = img.info[kunci]
        opsi.update(save_all=True, append_images=bingkai[1:])
    bingkai[0].save(hasil, fmt, **opsi)


def _hapus_metadata_gambar(sumber: Path, lapor: Callable[[float], None]) -> Path:
    ext = sumber.suffix.lstrip(".").lower()
    if ext in ("heic", "heif"):
        _daftarkan_heif()
    with Image.open(sumber) as img:
        img.load()
        lapor(0.3)
        hasil = keluaran.tujuan(sumber, ext, _AKHIRAN)
        try:
            _simpan_gambar(img, hasil, ext)
        except Exception:
            hasil.unlink(missing_ok=True)
            if ext not in ("heic", "heif"):
                raise
            # Penulis HEIF tidak tersedia: hasil disimpan sebagai JPEG.
            hasil = keluaran.tujuan(sumber, "jpg", _AKHIRAN)
            _simpan_gambar(img, hasil, "jpg")
    return hasil


def _hapus_metadata_media(sumber: Path) -> Path:
    hasil = keluaran.tujuan(sumber, sumber.suffix, _AKHIRAN)
    perintah = [
        biner("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(sumber),
        "-map", "0", "-map_metadata", "-1", "-map_chapters", "-1", "-c", "copy",
        "-fflags", "+bitexact", str(hasil),
    ]
    proses = subprocess.run(perintah, capture_output=True, text=True, errors="replace",
                            creationflags=TANPA_JENDELA)
    if proses.returncode != 0:
        hasil.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg gagal: {proses.stderr.strip()[-500:]}")
    return hasil


def _hapus_metadata_pdf(sumber: Path) -> Path:
    from pypdf import PdfWriter

    from jelma.mesin.pdf import _baca_pdf

    writer = PdfWriter(clone_from=_baca_pdf(sumber))
    writer.metadata = None
    writer.root_object.pop("/Metadata", None)
    for halaman in writer.pages:
        halaman.pop("/Metadata", None)
    hasil = keluaran.tujuan(sumber, "pdf", _AKHIRAN)
    with open(hasil, "wb") as f:
        writer.write(f)
    return hasil


def hapus_metadata(sumber: Path, lapor: Callable[[float], None], **_opsi) -> list[Path]:
    lapor(0.0)
    kelompok = kelompok_dari(sumber)
    if kelompok == "gambar":
        hasil = _hapus_metadata_gambar(sumber, lapor)
    elif kelompok in ("video", "audio"):
        hasil = _hapus_metadata_media(sumber)
    elif kelompok == "pdf":
        hasil = _hapus_metadata_pdf(sumber)
    else:
        raise RuntimeError(f"Jenis berkas tidak didukung: {sumber.suffix}")
    lapor(1.0)
    return [hasil]


def _salin_ke_clipboard(teks: str) -> None:
    try:
        import win32clipboard

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(teks, win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        pass  # clipboard sedang dipakai aplikasi lain; hasil tetap ada di berkas .txt


def baca_qr(sumber: Path, lapor: Callable[[float], None], **_opsi) -> list[Path]:
    import zxingcpp

    lapor(0.0)
    if sumber.suffix.lower() in (".heic", ".heif"):
        _daftarkan_heif()
    with Image.open(sumber) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
    lapor(0.3)
    kode = zxingcpp.read_barcodes(img)
    if not kode:
        kode = zxingcpp.read_barcodes(img.convert("L"))
    teks = [k.text for k in kode if k.text]
    if not teks:
        raise RuntimeError("QR code tidak ditemukan di gambar")
    lapor(0.8)
    gabungan = "\n".join(teks)
    hasil = keluaran.tujuan(sumber, "txt", " (QR)")
    hasil.write_text(gabungan + "\n", encoding="utf-8")
    _salin_ke_clipboard(gabungan)
    lapor(1.0)
    return [hasil]
