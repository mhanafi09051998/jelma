import hashlib
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from jelma.mesin import pdf


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _bising(ukuran: tuple[int, int]) -> Image.Image:
    return Image.effect_noise(ukuran, 60).convert("RGB")


@pytest.fixture
def pdf_bergambar(tmp_path: Path) -> Path:
    halaman = [_bising((2400, 1800)), Image.new("RGB", (800, 600), "red"), _bising((1200, 1600))]
    berkas = tmp_path / "dokumen.pdf"
    halaman[0].save(berkas, "PDF", save_all=True, append_images=halaman[1:], resolution=150.0)
    return berkas


def test_gambar_ke_pdf_rgba(tmp_path: Path):
    sumber = tmp_path / "logo.png"
    Image.new("RGBA", (300, 200), (0, 128, 255, 100)).save(sumber)
    awal = _hash(sumber)
    progres = []
    hasil = pdf.gambar_ke_pdf(sumber, progres.append)
    assert hasil == [tmp_path / "logo.pdf"]
    reader = PdfReader(hasil[0])
    assert len(reader.pages) == 1
    assert float(reader.pages[0].mediabox.width) == pytest.approx(300 * 72 / 150, abs=1)
    assert progres[0] == 0.0 and progres[-1] == 1.0
    assert _hash(sumber) == awal


def test_kompres_valid_dan_lebih_kecil(pdf_bergambar: Path):
    awal = _hash(pdf_bergambar)
    hasil = pdf.kompres(pdf_bergambar, lambda _p: None)
    assert hasil[0].name == "dokumen (kompres).pdf"
    reader = PdfReader(hasil[0])
    assert len(reader.pages) == 3
    assert hasil[0].stat().st_size < pdf_bergambar.stat().st_size
    gambar = reader.pages[0].images[0].image
    assert max(gambar.size) <= 1600
    assert _hash(pdf_bergambar) == awal


def test_kompres_pdf_terkunci(tmp_path: Path, pdf_bergambar: Path):
    writer = PdfWriter(clone_from=pdf_bergambar)
    writer.encrypt("rahasia", algorithm="AES-128")
    terkunci = tmp_path / "terkunci.pdf"
    with open(terkunci, "wb") as f:
        writer.write(f)
    with pytest.raises(RuntimeError, match="kata sandi"):
        pdf.kompres(terkunci, lambda _p: None)
    with pytest.raises(RuntimeError, match="kata sandi"):
        pdf.ke_gambar(terkunci, lambda _p: None, format="png")


@pytest.mark.parametrize("fmt", ["png", "jpg"])
def test_ke_gambar_per_halaman(pdf_bergambar: Path, fmt: str):
    awal = _hash(pdf_bergambar)
    progres = []
    hasil = pdf.ke_gambar(pdf_bergambar, progres.append, format=fmt)
    assert [p.name for p in hasil] == [f"halaman-00{i}.{fmt}" for i in (1, 2, 3)]
    assert all(p.parent == pdf_bergambar.with_name("dokumen") for p in hasil)
    with Image.open(hasil[1]) as img:
        # 800px @150dpi = 384pt; skala 2 -> 768px
        assert img.size == (768, 576)
        if fmt == "jpg":
            assert img.mode == "RGB"
    assert progres[-1] == 1.0 and len(progres) == 4
    assert _hash(pdf_bergambar) == awal
