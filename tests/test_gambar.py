import hashlib
from pathlib import Path

import pillow_heif
import pytest
from PIL import Image

from jelma.mesin import gambar

FORMAT = {"png": "PNG", "jpg": "JPEG", "webp": "WEBP", "avif": "AVIF", "bmp": "BMP",
          "gif": "GIF", "tiff": "TIFF", "ico": "ICO"}


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _diam(_p):
    pass


@pytest.fixture
def png_rgba(tmp_path):
    im = Image.new("RGBA", (300, 200), (255, 0, 0, 0))
    for x in range(100, 200):
        for y in range(50, 150):
            im.putpixel((x, y), (0, 0, 255, 255))
    p = tmp_path / "foto.png"
    im.save(p)
    return p


@pytest.fixture
def jpg_putar(tmp_path):
    # Piksel tersimpan 40x20, Orientation=6 (putar 90 derajat) -> tampil 20x40.
    im = Image.new("RGB", (40, 20), (10, 200, 10))
    exif = Image.Exif()
    exif[0x0112] = 6
    p = tmp_path / "putar.jpg"
    im.save(p, exif=exif.tobytes())
    return p


@pytest.fixture
def gif_animasi(tmp_path):
    bingkai = [Image.new("RGB", (64, 48), c) for c in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
    p = tmp_path / "gerak.gif"
    bingkai[0].save(p, save_all=True, append_images=bingkai[1:], duration=120, loop=0)
    return p


@pytest.fixture
def heic(tmp_path):
    p = tmp_path / "kamera.heic"
    pillow_heif.from_pillow(Image.new("RGB", (120, 80), (200, 100, 50))).save(p, quality=90)
    return p


@pytest.mark.parametrize("fmt", list(FORMAT))
def test_ke_format_dari_png_rgba(png_rgba, fmt):
    asli = _hash(png_rgba)
    progres = []
    hasil = gambar.ke_format(png_rgba, progres.append, format=fmt)
    assert len(hasil) == 1 and hasil[0].suffix == f".{fmt}"
    with Image.open(hasil[0]) as im:
        assert im.format == FORMAT[fmt]
        im.load()
    assert _hash(png_rgba) == asli
    assert progres[0] == 0.0 and progres[-1] == 1.0


def test_jpg_tanpa_alfa_berlatar_putih(png_rgba):
    [hasil] = gambar.ke_format(png_rgba, _diam, format="jpg")
    with Image.open(hasil) as im:
        assert im.mode == "RGB"
        r, g, b = im.getpixel((5, 5))
        assert min(r, g, b) > 240


def test_gif_mempertahankan_transparansi(png_rgba):
    [hasil] = gambar.ke_format(png_rgba, _diam, format="gif")
    with Image.open(hasil) as im:
        assert im.convert("RGBA").getpixel((5, 5))[3] == 0
        assert im.convert("RGBA").getpixel((150, 100))[3] == 255


def test_ico_berukuran_standar(png_rgba):
    [hasil] = gambar.ke_format(png_rgba, _diam, format="ico")
    with Image.open(hasil) as im:
        assert im.info["sizes"] == {(s, s) for s in (16, 32, 48, 64, 128, 256)}


def test_orientasi_exif_diterapkan(jpg_putar):
    [hasil] = gambar.ke_format(jpg_putar, _diam, format="png")
    with Image.open(hasil) as im:
        assert im.size == (20, 40)
        assert im.getexif().get(0x0112) in (None, 1)


@pytest.mark.parametrize("fmt", ["gif", "webp"])
def test_animasi_dipertahankan(gif_animasi, fmt):
    [hasil] = gambar.ke_format(gif_animasi, _diam, format=fmt)
    with Image.open(hasil) as im:
        assert im.n_frames == 3


def test_animasi_ke_png_bingkai_pertama(gif_animasi):
    [hasil] = gambar.ke_format(gif_animasi, _diam, format="png")
    with Image.open(hasil) as im:
        assert getattr(im, "n_frames", 1) == 1
        assert im.convert("RGB").getpixel((1, 1)) == (255, 0, 0)


def test_heic_ke_jpg(heic):
    asli = _hash(heic)
    [hasil] = gambar.ke_format(heic, _diam, format="jpg")
    with Image.open(hasil) as im:
        assert im.format == "JPEG" and im.size == (120, 80)
    assert _hash(heic) == asli


def test_kompres_heic_jadi_jpg(heic):
    [hasil] = gambar.kompres(heic, _diam)
    assert hasil.name == "kamera (kompres).jpg"


@pytest.mark.parametrize("nama", ["foto.png", "foto.jpg", "foto.webp"])
def test_kompres_format_sama(tmp_path, nama):
    sumber = tmp_path / nama
    Image.effect_noise((200, 200), 40).convert("RGB").save(sumber)
    asli = _hash(sumber)
    [hasil] = gambar.kompres(sumber, _diam)
    assert hasil.name == f"foto (kompres){sumber.suffix}"
    with Image.open(hasil) as im, Image.open(sumber) as src:
        assert im.format == src.format
    assert _hash(sumber) == asli


def test_kompres_png_alfa_utuh(png_rgba):
    [hasil] = gambar.kompres(png_rgba, _diam)
    with Image.open(hasil) as im:
        rgba = im.convert("RGBA")
        assert rgba.getpixel((5, 5))[3] == 0 and rgba.getpixel((150, 100))[3] == 255


def test_ubah_ukuran(png_rgba):
    [hasil] = gambar.ubah_ukuran(png_rgba, _diam, skala=0.5)
    assert hasil.name == "foto (50%).png"
    with Image.open(hasil) as im:
        assert im.size == (150, 100)


def test_ubah_ukuran_gif_animasi(gif_animasi):
    [hasil] = gambar.ubah_ukuran(gif_animasi, _diam, skala=0.5)
    with Image.open(hasil) as im:
        assert im.size == (32, 24) and im.n_frames == 3


def test_ubah_ukuran_heic(heic):
    [hasil] = gambar.ubah_ukuran(heic, _diam, skala=0.5)
    assert hasil.name == "kamera (50%).jpg"
    with Image.open(hasil) as im:
        assert im.size == (60, 40)


def test_nama_bentrok_diberi_nomor(png_rgba):
    [a] = gambar.ke_format(png_rgba, _diam, format="webp")
    [b] = gambar.ke_format(png_rgba, _diam, format="webp")
    assert a.name == "foto.webp" and b.name == "foto (1).webp"


def test_format_tak_dikenal(png_rgba):
    with pytest.raises(ValueError):
        gambar.ke_format(png_rgba, _diam, format="xyz")
