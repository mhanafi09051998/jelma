import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import pytest

from jelma import antrean, daftar_aksi, jendela, ui_tk

AKSI = "gambar-ke-webp"
REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def lingkungan(monkeypatch, tmp_path):
    """Pipe unik per tes, mesin palsu, dan jendela/Tk dimatikan."""
    monkeypatch.setattr(antrean, "ALAMAT", rf"\\.\pipe\jelma-uji-{uuid.uuid4().hex}")
    monkeypatch.setattr(antrean, "JEDA_BERHENTI", 0.3)
    dikerjakan, kabar = [], []

    def jalankan_palsu(aksi_id, sumber, lapor=lambda _p: None):
        lapor(0.5)
        if sumber.name.startswith("rusak"):
            raise RuntimeError("mesin gagal")
        dikerjakan.append((aksi_id, sumber.name))
        return [sumber.with_suffix(".webp")]

    monkeypatch.setattr(daftar_aksi, "jalankan", jalankan_palsu)
    for nama in ("mulai_tugas", "progres", "selesai"):
        monkeypatch.setattr(jendela, nama, lambda *a, n=nama: kabar.append((n, a)))
    monkeypatch.setattr(jendela, "galat", lambda pesan: kabar.append(("galat", pesan)))
    monkeypatch.setattr(jendela, "tampil", lambda: False)
    berhenti = threading.Event()
    monkeypatch.setattr(ui_tk, "berhenti", berhenti.set)
    monkeypatch.setattr(ui_tk, "jalankan_loop", lambda: berhenti.wait(10))

    def berkas(nama):
        p = tmp_path / nama
        p.write_bytes(b"x")
        return str(p)

    return dikerjakan, kabar, berkas, berhenti


def _tunggu(syarat, batas=5.0):
    akhir = time.monotonic() + batas
    while not syarat():
        assert time.monotonic() < akhir, "waktu tunggu habis"
        time.sleep(0.02)


def test_kirim_tanpa_server_cepat_false(lingkungan):
    mulai = time.perf_counter()
    assert antrean.kirim([(AKSI, "a.png")]) is False
    assert time.perf_counter() - mulai < 0.3


def test_server_kedua_ditolak(lingkungan):
    assert antrean.mulai_server(True)
    assert not antrean.mulai_server(True)


def test_banyak_klien_serentak_sekali_dan_urut(lingkungan):
    dikerjakan, kabar, berkas, _ = lingkungan
    assert antrean.mulai_server(True)
    jumlah_klien, per_klien = 8, 5
    kiriman = [[(AKSI, berkas(f"k{k}-{i}.png")) for i in range(per_klien)] for k in range(jumlah_klien)]
    hasil = [None] * jumlah_klien
    gerbang = threading.Barrier(jumlah_klien)

    def klien(k):
        gerbang.wait()
        hasil[k] = antrean.kirim(kiriman[k])

    utas = [threading.Thread(target=klien, args=(k,)) for k in range(jumlah_klien)]
    for u in utas:
        u.start()
    for u in utas:
        u.join(10)
    assert all(hasil)
    _tunggu(lambda: len(dikerjakan) == jumlah_klien * per_klien)
    time.sleep(0.2)
    nama = [n for _, n in dikerjakan]
    assert len(nama) == len(set(nama)) == jumlah_klien * per_klien
    # Tiap kiriman masuk utuh dan berurutan, tidak diselang kiriman lain.
    for i in range(0, len(nama), per_klien):
        blok = nama[i:i + per_klien]
        k = blok[0].split("-")[0]
        assert blok == [f"{k}-{j}.png" for j in range(per_klien)]
    assert sum(1 for n, _ in kabar if n == "selesai") == jumlah_klien * per_klien


def test_tugas_tidak_sah_dan_mesin_gagal_dilaporkan(lingkungan):
    dikerjakan, kabar, berkas, berhenti = lingkungan
    tugas = [("aksi-palsu", berkas("a.png")), (AKSI, r"C:\tidak\ada.png"),
             (AKSI, berkas("rusak.png")), (AKSI, berkas("bagus.png"))]
    assert antrean.jalankan_mandiri(tugas) == 1
    galat = [p for n, p in kabar if n == "galat"]
    assert galat == ["a.png: aksi tidak dikenal (aksi-palsu)", "ada.png: berkas tidak ditemukan",
                     "rusak.png: mesin gagal"]
    assert dikerjakan == [(AKSI, "bagus.png")]
    assert berhenti.is_set()


def test_mandiri_berhenti_saat_diam_lalu_menolak_kiriman(lingkungan):
    dikerjakan, kabar, berkas, berhenti = lingkungan
    assert antrean.jalankan_mandiri([(AKSI, berkas("a.png")), (AKSI, berkas("b.png"))]) == 0
    assert [n for _, n in dikerjakan] == ["a.png", "b.png"]
    mulai = [a for n, a in kabar if n == "mulai_tugas"]
    assert mulai == [("a.png", "Ke WEBP", 1), ("b.png", "Ke WEBP", 0)]
    # Pipe masih dipegang sampai proses keluar, tetapi server yang menutup tidak menerima tugas baru.
    assert antrean.kirim([(AKSI, berkas("c.png"))]) is False


def test_server_menunggu_jendela_tertutup(lingkungan, monkeypatch):
    _, _, berkas, berhenti = lingkungan
    terbuka = [True]
    monkeypatch.setattr(jendela, "tampil", lambda: terbuka[0])
    assert antrean.mulai_server(False)
    antrean.tambah([(AKSI, berkas("a.png"))])
    time.sleep(0.8)
    assert not berhenti.is_set()
    terbuka[0] = False
    _tunggu(berhenti.is_set)


SKRIP_BALAPAN = r"""
import sys, threading
sys.path.insert(0, sys.argv[1])
from jelma import antrean, daftar_aksi, jendela, ui_tk
antrean.ALAMAT = sys.argv[2]
log = sys.argv[3]
def jalankan(aksi_id, sumber, lapor=None):
    with open(log, "a", encoding="utf-8") as f:
        f.write(sumber.name + "\n")
    return []
daftar_aksi.jalankan = jalankan
for n in ("mulai_tugas", "progres", "selesai", "galat"):
    setattr(jendela, n, lambda *a: None)
jendela.tampil = lambda: False
ev = threading.Event()
ui_tk.berhenti = ev.set
ui_tk.jalankan_loop = lambda: ev.wait(15)
tugas = [("gambar-ke-webp", sys.argv[4])]
sys.exit(0 if antrean.kirim(tugas) else antrean.jalankan_mandiri(tugas))
"""


def test_balapan_banyak_proses_explorer(tmp_path):
    """Seperti Explorer membuka N proses sekaligus: satu memegang pipe, sisanya menitip; semua dikerjakan sekali."""
    skrip = tmp_path / "balapan.py"
    skrip.write_text(SKRIP_BALAPAN, encoding="utf-8")
    alamat = rf"\\.\pipe\jelma-uji-{uuid.uuid4().hex}"
    log = tmp_path / "log.txt"
    nama = [f"f{i}.png" for i in range(8)]
    for n in nama:
        (tmp_path / n).write_bytes(b"x")
    proses = [subprocess.Popen([sys.executable, str(skrip), str(REPO), alamat, str(log), str(tmp_path / n)])
              for n in nama]
    kode = [p.wait(30) for p in proses]
    assert kode == [0] * len(nama)
    terkerjakan = log.read_text(encoding="utf-8").split()
    assert sorted(terkerjakan) == sorted(nama)
