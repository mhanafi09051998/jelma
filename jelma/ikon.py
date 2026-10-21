"""Ikon aplikasi: kotak yang menjelma lingkaran di atas ubin gradasi hijau-teal.

`python -m jelma.ikon` menulis ulang aset/jelma.ico dan aset/jelma.png.
"""
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

UKURAN_ICO = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
_GRADASI = ((22, 163, 74), (20, 184, 166))  # hijau-600 -> teal-500
_SUPER = 4  # digambar 4x lalu diperkecil agar tepi halus


def jalur_ico() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "aset" / "jelma.ico"
    return Path(__file__).resolve().parent.parent / "aset" / "jelma.ico"


def _gradasi(s: int) -> Image.Image:
    # Gradasi diagonal kiri-atas -> kanan-bawah.
    garis = Image.linear_gradient("L").resize((s, s))
    miring = ImageChops.add(garis, garis.rotate(90), scale=2)
    awal = Image.new("RGB", (s, s), _GRADASI[0])
    akhir = Image.new("RGB", (s, s), _GRADASI[1])
    return Image.composite(akhir, awal, miring)


def buat_gambar(sisi: int = 256) -> Image.Image:
    s = sisi * _SUPER
    ubin = Image.new("L", (s, s), 0)
    ImageDraw.Draw(ubin).rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.22), fill=255)
    img = _gradasi(s).convert("RGBA")
    img.putalpha(ubin)

    # Kotak (wujud asal) dan lingkaran (wujud baru) saling menimpa; irisannya dilubangi.
    kotak = Image.new("L", (s, s), 0)
    ImageDraw.Draw(kotak).rounded_rectangle(
        (int(s * 0.17), int(s * 0.17), int(s * 0.61), int(s * 0.61)), radius=int(s * 0.07), fill=255)
    bulat = Image.new("L", (s, s), 0)
    ImageDraw.Draw(bulat).ellipse((int(s * 0.39), int(s * 0.39), int(s * 0.83), int(s * 0.83)), fill=255)
    bentuk = ImageChops.logical_xor(kotak.convert("1"), bulat.convert("1")).convert("L")

    putih = Image.new("RGBA", (s, s), (255, 255, 255, 255))
    img.paste(putih, (0, 0), ImageChops.multiply(bentuk, ubin))
    return img.resize((sisi, sisi), Image.LANCZOS)


def tulis_ico(tujuan: Path | None = None) -> Path:
    tujuan = tujuan or jalur_ico()
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    buat_gambar(256).save(tujuan, format="ICO", sizes=UKURAN_ICO)
    buat_gambar(512).save(tujuan.with_suffix(".png"))
    return tujuan


def gambar_tray() -> Image.Image:
    """Ikon untuk pystray; bila aset hilang, digambar di memori."""
    try:
        with Image.open(jalur_ico()) as ico:
            return ico.convert("RGBA")
    except OSError:
        return buat_gambar(64)


if __name__ == "__main__":
    print(tulis_ico())
