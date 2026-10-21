import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
import zxingcpp
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter

from jelma.mesin import alat

GPS = 0x8825
ORIENTASI = 0x0112


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(autouse=True)
def clipboard_palsu(monkeypatch):
    disalin: list[str] = []
    monkeypatch.setattr(alat, "_salin_ke_clipboard", disalin.append)
    return disalin


def _jpeg_ber_gps(path: Path, orientasi: int = 1) -> None:
    img = Image.new("RGB", (40, 20), "white")
    img.paste((255, 0, 0), (0, 0, 20, 20))  # kiri merah, kanan putih
    exif = Image.Exif()
    exif[0x010F] = "KameraContoh"
    exif[ORIENTASI] = orientasi
    exif.get_ifd(GPS).update({1: "S", 2: (6.0, 10.0, 0.0), 3: "E", 4: (106.0, 49.0, 0.0)})
    img.save(path, "JPEG", exif=exif, quality=90, comment=b"rahasia")


def test_hapus_metadata_jpeg_tanpa_rotasi(tmp_path: Path):
    sumber = tmp_path / "foto.jpg"
    _jpeg_ber_gps(sumber)
    awal = _hash(sumber)
    hasil = alat.hapus_metadata(sumber, lambda _p: None)
    assert hasil == [tmp_path / "foto (tanpa metadata).jpg"]
    with Image.open(hasil[0]) as img, Image.open(sumber) as asli:
        assert not img.getexif()
        assert "comment" not in img.info and "exif" not in img.info
        assert img.quantization == asli.quantization
        assert img.size == asli.size
    assert _hash(sumber) == awal


def test_hapus_metadata_jpeg_berorientasi(tmp_path: Path):
    sumber = tmp_path / "putar.jpg"
    _jpeg_ber_gps(sumber, orientasi=6)
    hasil = alat.hapus_metadata(sumber, lambda _p: None)
    with Image.open(hasil[0]) as img, Image.open(sumber) as asli:
        assert not img.getexif()
        tegak = ImageOps.exif_transpose(asli)
        assert img.size == tegak.size == (20, 40)


def test_hapus_metadata_png_jaga_icc(tmp_path: Path):
    from PIL import ImageCms

    from PIL.PngImagePlugin import PngInfo

    sumber = tmp_path / "gambar.png"
    teks = PngInfo()
    teks.add_text("Author", "Budi")
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    exif = Image.Exif()
    exif.get_ifd(GPS)[1] = "S"
    Image.new("RGBA", (10, 10), (1, 2, 3, 128)).save(sumber, pnginfo=teks, icc_profile=icc, exif=exif)
    hasil = alat.hapus_metadata(sumber, lambda _p: None)
    with Image.open(hasil[0]) as img:
        assert "Author" not in img.info and not img.getexif()
        assert img.info.get("icc_profile") == icc
        assert img.mode == "RGBA" and img.getpixel((0, 0)) == (1, 2, 3, 128)


def _ffprobe(path: Path) -> dict:
    keluar = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(keluar.stdout)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg tidak ada")
def test_hapus_metadata_video(tmp_path: Path):
    sumber = tmp_path / "klip.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=10:duration=1",
         "-f", "lavfi", "-i", "sine=duration=1", "-shortest", "-c:v", "libx264", "-c:a", "aac",
         "-metadata", "title=rahasia", "-metadata", "artist=budi", str(sumber)],
        check=True, capture_output=True,
    )
    assert _ffprobe(sumber)["format"]["tags"]["title"] == "rahasia"
    awal = _hash(sumber)
    hasil = alat.hapus_metadata(sumber, lambda _p: None)
    assert hasil[0].name == "klip (tanpa metadata).mp4"
    info = _ffprobe(hasil[0])
    tags = info["format"].get("tags", {})
    assert "title" not in tags and "artist" not in tags
    assert {s["codec_type"] for s in info["streams"]} == {"video", "audio"}
    assert _hash(sumber) == awal


def test_hapus_metadata_pdf(tmp_path: Path):
    sumber = tmp_path / "surat.pdf"
    writer = PdfWriter()
    writer.add_blank_page(200, 200)
    writer.add_metadata({"/Author": "Budi", "/Title": "Rahasia"})
    with open(sumber, "wb") as f:
        writer.write(f)
    awal = _hash(sumber)
    hasil = alat.hapus_metadata(sumber, lambda _p: None)
    reader = PdfReader(hasil[0])
    assert reader.metadata is None
    assert "/Metadata" not in reader.trailer["/Root"]
    assert len(reader.pages) == 1
    assert _hash(sumber) == awal


def _gambar_qr(teks: str) -> Image.Image:
    kode = zxingcpp.create_barcode(teks, zxingcpp.BarcodeFormat.QRCode)
    return Image.fromarray(np.array(kode.to_image(scale=8)))


def test_baca_qr(tmp_path: Path, clipboard_palsu):
    sumber = tmp_path / "kode.png"
    _gambar_qr("https://contoh.id/halo — ünïcode").save(sumber)
    awal = _hash(sumber)
    hasil = alat.baca_qr(sumber, lambda _p: None)
    assert hasil == [tmp_path / "kode (QR).txt"]
    assert hasil[0].read_text(encoding="utf-8").strip() == "https://contoh.id/halo — ünïcode"
    assert clipboard_palsu == ["https://contoh.id/halo — ünïcode"]
    assert _hash(sumber) == awal


def test_baca_qr_banyak_kode(tmp_path: Path):
    kanvas = Image.new("L", (600, 300), 255)
    kanvas.paste(_gambar_qr("satu"), (20, 20))
    kanvas.paste(_gambar_qr("dua"), (330, 20))
    sumber = tmp_path / "dua.png"
    kanvas.save(sumber)
    teks = alat.baca_qr(sumber, lambda _p: None)[0].read_text(encoding="utf-8").split()
    assert sorted(teks) == ["dua", "satu"]


def test_baca_qr_tidak_ada(tmp_path: Path):
    sumber = tmp_path / "polos.png"
    Image.new("RGB", (100, 100), "white").save(sumber)
    with pytest.raises(RuntimeError, match="QR code tidak ditemukan"):
        alat.baca_qr(sumber, lambda _p: None)
    assert not (tmp_path / "polos (QR).txt").exists()
