"""Mesin PDF: gambar ke PDF, kompres PDF, dan PDF ke gambar per halaman."""
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps

from jelma import keluaran

_SISI_MAKS = 1600
_MUTU_JPEG = 60


def _buka_gambar(sumber: Path) -> Image.Image:
    if sumber.suffix.lower() in (".heic", ".heif"):
        import pillow_heif
        pillow_heif.register_heif_opener()
    img = Image.open(sumber)
    img.load()
    return ImageOps.exif_transpose(img)


def _ke_rgb(img: Image.Image) -> Image.Image:
    """Transparansi ditumpuk di atas latar putih; PDF dan JPEG tidak menyimpan alpha."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        latar = Image.new("RGB", rgba.size, "white")
        latar.paste(rgba, mask=rgba.getchannel("A"))
        return latar
    return img if img.mode in ("RGB", "L") else img.convert("RGB")


def gambar_ke_pdf(sumber: Path, lapor: Callable[[float], None], **_opsi) -> list[Path]:
    lapor(0.0)
    img = _ke_rgb(_buka_gambar(sumber))
    lapor(0.5)
    hasil = keluaran.tujuan(sumber, "pdf")
    img.save(hasil, "PDF", resolution=150.0)
    lapor(1.0)
    return [hasil]


def _baca_pdf(sumber: Path):
    from pypdf import PdfReader

    reader = PdfReader(sumber)
    if reader.is_encrypted:
        try:
            terbuka = reader.decrypt("")
        except Exception:
            terbuka = 0
        if not terbuka:
            raise RuntimeError("PDF terkunci kata sandi")
    return reader


def _kompres_gambar(gambar) -> None:
    """Satu gambar tersemat: perkecil bila terlalu besar lalu simpan ulang sebagai JPEG."""
    img = gambar.image
    if img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info:
        return  # alpha di PDF disimpan sebagai SMask terpisah; JPEG akan merusaknya
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if max(img.size) > _SISI_MAKS:
        img = img.copy()
        img.thumbnail((_SISI_MAKS, _SISI_MAKS), Image.Resampling.LANCZOS)
    gambar.replace(img, quality=_MUTU_JPEG)


def kompres(sumber: Path, lapor: Callable[[float], None], **_opsi) -> list[Path]:
    from pypdf import PdfWriter

    lapor(0.0)
    writer = PdfWriter(clone_from=_baca_pdf(sumber))
    jumlah = len(writer.pages) or 1
    for i, halaman in enumerate(writer.pages):
        for gambar in halaman.images:
            try:
                _kompres_gambar(gambar)
            except Exception:
                continue  # filter/warna yang tidak didukung: biarkan gambar aslinya
        halaman.compress_content_streams()
        lapor(0.9 * (i + 1) / jumlah)
    writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    hasil = keluaran.tujuan(sumber, "pdf", " (kompres)")
    with open(hasil, "wb") as f:
        writer.write(f)
    lapor(1.0)
    return [hasil]


def ke_gambar(sumber: Path, lapor: Callable[[float], None], format: str = "png", **_opsi) -> list[Path]:
    import pypdfium2 as pdfium

    fmt = "jpg" if format.lower() in ("jpg", "jpeg") else "png"
    lapor(0.0)
    try:
        dok = pdfium.PdfDocument(str(sumber))
    except pdfium.PdfiumError as e:
        if "password" in str(e).lower():
            raise RuntimeError("PDF terkunci kata sandi") from e
        raise
    try:
        jumlah = len(dok)
        folder = keluaran.folder_tujuan(sumber)
        hasil: list[Path] = []
        for i in range(jumlah):
            halaman = dok[i]
            img = halaman.render(scale=2).to_pil()
            halaman.close()
            berkas = folder / f"halaman-{i + 1:03d}.{fmt}"
            if fmt == "jpg":
                _ke_rgb(img).convert("RGB").save(berkas, "JPEG", quality=90)
            else:
                img.save(berkas, "PNG")
            hasil.append(berkas)
            lapor((i + 1) / jumlah)
    finally:
        dok.close()
    return hasil
