"""Mesin gambar: ganti format, kompres, dan ubah ukuran (Pillow + pillow_heif)."""
from io import BytesIO
from pathlib import Path

import pillow_heif
from PIL import Image, ImageChops, ImageOps, ImageSequence, features

from jelma import keluaran

pillow_heif.register_heif_opener()
if not features.check("avif"):
    pillow_heif.register_avif_opener()

_PIL = {"png": "PNG", "jpg": "JPEG", "webp": "WEBP", "avif": "AVIF", "bmp": "BMP",
        "gif": "GIF", "tiff": "TIFF", "ico": "ICO"}
_ALIAS = {"jpeg": "jpg", "tif": "tiff", "heif": "heic"}
_ANIMASI = {"gif", "webp"}
_ICC = {"png", "jpg", "webp", "avif", "tiff"}
_EXIF = {"png", "jpg", "webp", "avif", "tiff"}
_UKURAN_ICO = [16, 32, 48, 64, 128, 256]
# Mode yang diterima tiap format tanpa konversi; selain itu diubah ke RGB/RGBA.
_MODE_OK = {
    "jpg": {"RGB", "L"}, "bmp": {"RGB", "L"}, "webp": {"RGB", "RGBA"}, "avif": {"RGB", "RGBA"},
    "png": {"RGB", "RGBA", "L", "LA", "I;16"}, "tiff": {"RGB", "RGBA", "L", "LA", "CMYK"},
    "gif": {"RGB", "RGBA", "L"}, "ico": {"RGBA"},
}
_MUTU = {"jpg": 90, "webp": 85, "avif": 70}
_MUTU_KOMPRES = {"jpg": 75, "webp": 75, "avif": 50}


def _ext(sumber: Path) -> str:
    ext = sumber.suffix.lstrip(".").lower()
    return _ALIAS.get(ext, ext)


def _beralfa(im: Image.Image) -> bool:
    return im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info


def _normal(im: Image.Image) -> Image.Image:
    """Palet/1-bit/CMYK diubah ke RGB(A) agar resize LANCZOS dan komposit berjalan benar."""
    if im.mode in ("P", "PA", "1"):
        return im.convert("RGBA" if _beralfa(im) else "RGB")
    if im.mode not in ("RGB", "RGBA", "L", "LA", "I;16", "CMYK"):
        return im.convert("RGBA" if _beralfa(im) else "RGB")
    return im


def _baca(im: Image.Image, animasi: bool, lapor) -> tuple[list[Image.Image], list[int]]:
    """Kembalikan bingkai (orientasi EXIF sudah diterapkan) beserta durasinya."""
    if not animasi:
        return [_normal(ImageOps.exif_transpose(im))], []
    bingkai, durasi = [], []
    total = im.n_frames
    for i, fr in enumerate(ImageSequence.Iterator(im)):
        bingkai.append(fr.convert("RGBA"))
        durasi.append(int(fr.info.get("duration", im.info.get("duration", 100)) or 100))
        lapor(0.1 + 0.4 * (i + 1) / total)
    return bingkai, durasi


def _siapkan(im: Image.Image, fmt: str) -> Image.Image:
    """Sesuaikan mode dengan kemampuan format tujuan."""
    if fmt == "ico":
        im = im.convert("RGBA")
        sisi = max(im.size)
        if im.width != im.height:
            kanvas = Image.new("RGBA", (sisi, sisi), (0, 0, 0, 0))
            kanvas.paste(im, ((sisi - im.width) // 2, (sisi - im.height) // 2))
            im = kanvas
        if sisi > 256:
            im = im.resize((256, 256), Image.Resampling.LANCZOS)
        return im
    if im.mode in _MODE_OK[fmt]:
        return im
    if fmt in ("jpg", "bmp") and _beralfa(im):
        # Tanpa kanal alfa: tempel di atas latar putih.
        rgba = im.convert("RGBA")
        latar = Image.new("RGB", rgba.size, (255, 255, 255))
        latar.paste(rgba, mask=rgba.getchannel("A"))
        return latar
    return im.convert("RGBA" if _beralfa(im) and "RGBA" in _MODE_OK[fmt] else "RGB")


def _opsi_simpan(fmt: str, kuat: bool, info: dict, im: Image.Image) -> dict:
    opsi: dict = {}
    mutu = (_MUTU_KOMPRES if kuat else _MUTU).get(fmt)
    if mutu:
        opsi["quality"] = mutu
    if fmt == "jpg" and kuat:
        opsi.update(optimize=True, progressive=True)
    elif fmt == "webp":
        opsi["method"] = 6
    elif fmt in ("png", "gif"):
        opsi["optimize"] = kuat or fmt == "gif"
    elif fmt == "tiff":
        opsi["compression"] = "tiff_adobe_deflate" if kuat else "tiff_lzw"
    elif fmt == "ico":
        opsi["sizes"] = [(s, s) for s in _UKURAN_ICO if s <= im.width] or [im.size]
    if fmt in _ICC and info.get("icc_profile") and info.get("_mode_asal") != "CMYK":
        opsi["icc_profile"] = info["icc_profile"]
    if fmt in _EXIF and info.get("exif"):
        opsi["exif"] = info["exif"]
    return opsi


def _ke_bita(bingkai: list[Image.Image], durasi: list[int], fmt: str, opsi: dict, loop) -> bytes:
    buf = BytesIO()
    if len(bingkai) > 1:
        tambahan = {"save_all": True, "append_images": bingkai[1:], "duration": durasi, "loop": loop}
        if fmt == "gif":
            tambahan["disposal"] = 2
        bingkai[0].save(buf, _PIL[fmt], **opsi, **tambahan)
    else:
        bingkai[0].save(buf, _PIL[fmt], **opsi)
    return buf.getvalue()


def _png_terkuantisasi(im: Image.Image, opsi: dict, data: bytes) -> bytes:
    """Coba palet 256 warna; dipakai hanya bila lebih kecil dan kanal alfa tetap utuh."""
    if im.mode not in ("RGB", "RGBA"):
        return data
    metode = Image.Quantize.FASTOCTREE if im.mode == "RGBA" else Image.Quantize.MEDIANCUT
    q = im.quantize(256, method=metode)
    if im.mode == "RGBA":
        alfa_q = q.convert("RGBA").getchannel("A")
        if ImageChops.difference(im.getchannel("A"), alfa_q).getbbox() is not None:
            return data
    buf = BytesIO()
    q.save(buf, "PNG", **opsi)
    return buf.getvalue() if buf.tell() < len(data) else data


def _proses(sumber: Path, lapor, fmt: str, ext: str, akhiran: str = "",
            ubah=None, kuat: bool = False) -> list[Path]:
    sumber = Path(sumber)
    lapor(0.0)
    with Image.open(sumber) as im:
        animasi = fmt in _ANIMASI and getattr(im, "n_frames", 1) > 1
        info = dict(im.info, _mode_asal=im.mode)
        loop = im.info.get("loop", 0)
        bingkai, durasi = _baca(im, animasi, lapor)
    if not animasi:
        # EXIF dari bingkai yang sudah diputar: tag Orientation telah dihapus, mencegah putar ganda.
        info["exif"] = bingkai[0].info.get("exif")
    lapor(0.5)
    if ubah:
        bingkai = [ubah(b) for b in bingkai]
    bingkai = [_siapkan(b, fmt) for b in bingkai]
    lapor(0.7)
    opsi = _opsi_simpan(fmt, kuat, info, bingkai[0])
    data = _ke_bita(bingkai, durasi, fmt, opsi, loop)
    if kuat and fmt == "png" and len(bingkai) == 1:
        data = _png_terkuantisasi(bingkai[0], opsi, data)
    lapor(0.9)
    hasil = keluaran.tujuan(sumber, ext, akhiran)
    hasil.write_bytes(data)
    lapor(1.0)
    return [hasil]


def _format_sama(sumber: Path) -> tuple[str, str]:
    """Format & ekstensi hasil untuk aksi yang mempertahankan format; HEIC menjadi JPG."""
    fmt = _ext(Path(sumber))
    if fmt not in _PIL:
        return "jpg", "jpg"
    return fmt, Path(sumber).suffix.lstrip(".").lower()


def ke_format(sumber: Path, lapor, format: str) -> list[Path]:
    fmt = _ALIAS.get(format.lower(), format.lower())
    if fmt not in _PIL:
        raise ValueError(f"Format tujuan tidak didukung: {format}")
    return _proses(sumber, lapor, fmt, fmt)


def kompres(sumber: Path, lapor) -> list[Path]:
    fmt, ext = _format_sama(sumber)
    return _proses(sumber, lapor, fmt, ext, " (kompres)", kuat=True)


def ubah_ukuran(sumber: Path, lapor, skala: float) -> list[Path]:
    if skala <= 0:
        raise ValueError("Skala harus lebih dari 0")
    fmt, ext = _format_sama(sumber)

    def ubah(im: Image.Image) -> Image.Image:
        ukuran = (max(1, round(im.width * skala)), max(1, round(im.height * skala)))
        return im.resize(ukuran, Image.Resampling.LANCZOS)

    return _proses(sumber, lapor, fmt, ext, f" ({round(skala * 100)}%)", ubah=ubah)
