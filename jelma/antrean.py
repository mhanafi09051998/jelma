"""Antrean tugas satu-instans lewat named pipe per pengguna.

Explorer menjalankan satu proses per berkas terpilih. Proses pertama memegang pipe dan mengerjakan
semua tugas berurutan; proses lain cukup `kirim()` lalu keluar. Isi pesan JSON (bukan pickle),
jadi klien yang lolos autentikasi pun tidak bisa menjalankan kode di proses server.
"""
import getpass
import hashlib
import json
import queue
import sys
import threading
import time
from multiprocessing import AuthenticationError
from multiprocessing.connection import Client, Listener
from pathlib import Path

from jelma import daftar_aksi, jendela, ui_tk

_PENGGUNA = getpass.getuser().lower()
ALAMAT = rf"\\.\pipe\jelma-{_PENGGUNA}"
KUNCI = hashlib.sha256(f"jelma-antrean/{_PENGGUNA}".encode()).digest()
JEDA_BERHENTI = 1.5   # detik diam setelah jendela tertutup sebelum loop Tk dihentikan
BATAS_PESAN = 1 << 20
_GALAT_SAMBUNG = (OSError, EOFError, AuthenticationError)


class _Keadaan:
    """Status satu server. Thread memegang objeknya sendiri, jadi server baru tidak berbagi antrean lama."""

    def __init__(self):
        self.antrean: queue.Queue = queue.Queue()
        self.kunci = threading.Lock()
        self.menutup = False
        self.gagal = 0
        self.berhenti = threading.Event()


_k = _Keadaan()


def kirim(tugas: list[tuple[str, str]]) -> bool:
    """Serahkan tugas ke server yang sedang jalan. False bila tidak ada server atau server sedang menutup."""
    try:
        with Client(ALAMAT, family="AF_PIPE", authkey=KUNCI) as conn:
            conn.send_bytes(json.dumps([[a, str(b)] for a, b in tugas]).encode())
            return conn.poll(5) and conn.recv_bytes(16) == b"1"
    except _GALAT_SAMBUNG:
        return False


def mulai_server(tetap_hidup: bool) -> bool:
    """Pegang pipe dan jalankan thread pendengar + worker. False bila pipe sudah dimiliki proses lain.

    Panggil dari thread utama sebelum `ui_tk.jalankan_loop()`.
    """
    global _k
    try:
        pendengar = Listener(ALAMAT, family="AF_PIPE", authkey=KUNCI)
    except OSError:
        return False
    _k = k = _Keadaan()
    threading.Thread(target=_dengar, args=(pendengar, k), name="jelma-pipe", daemon=True).start()
    threading.Thread(target=_kerja, args=(k, tetap_hidup), name="jelma-worker", daemon=True).start()
    return True


def tambah(tugas: list[tuple[str, str]]) -> None:
    with _k.kunci:
        _masukkan(_k, tugas)


def jalankan_mandiri(tugas: list[tuple[str, str]]) -> int:
    """Jadi server sementara untuk tugas ini; bila kalah balapan dengan proses lain, titipkan ke sana."""
    batas = time.monotonic() + 3
    while not mulai_server(False):
        if kirim(tugas):
            return 0
        if time.monotonic() > batas:
            print("jelma: antrean sedang dipakai proses lain dan tidak menjawab", file=sys.stderr)
            return 1
        time.sleep(0.1)
    k = _k
    tambah(tugas)
    ui_tk.jalankan_loop()
    return 0 if k.gagal == 0 else 1


def _masukkan(k: _Keadaan, tugas) -> None:
    """Validasi di sini, tetapi galat dilaporkan lewat worker agar urutannya sama dengan antrean."""
    for aksi_id, berkas in tugas:
        pesan = None
        if aksi_id not in daftar_aksi.SEMUA:
            pesan = f"aksi tidak dikenal ({aksi_id})"
        elif not Path(berkas).is_file():
            pesan = "berkas tidak ditemukan"
        k.antrean.put((aksi_id, str(berkas), pesan))


def _terima(k: _Keadaan, data: bytes) -> bool:
    try:
        tugas = [(str(a), str(b)) for a, b in json.loads(data)]
    except (ValueError, TypeError):
        return False
    with k.kunci:
        if k.menutup:
            return False
        _masukkan(k, tugas)
        return True


def _dengar(pendengar: Listener, k: _Keadaan) -> None:
    # Koneksi dilayani satu per satu: urutan masuk antrean = urutan diterima.
    while True:
        try:
            conn = pendengar.accept()
        except _GALAT_SAMBUNG:
            continue
        with conn:
            try:
                if conn.poll(2):
                    conn.send_bytes(b"1" if _terima(k, conn.recv_bytes(BATAS_PESAN)) else b"0")
            except _GALAT_SAMBUNG:
                pass


def _kerja(k: _Keadaan, tetap_hidup: bool) -> None:
    sejak_diam = None
    while True:
        try:
            item = k.antrean.get(timeout=None if tetap_hidup else 0.1)
        except queue.Empty:
            if jendela.tampil():
                sejak_diam = None
                continue
            sejak_diam = sejak_diam or time.monotonic()
            if time.monotonic() - sejak_diam < JEDA_BERHENTI:
                continue
            with k.kunci:
                if not k.antrean.empty():
                    continue
                k.menutup = True
            k.berhenti.set()
            ui_tk.berhenti()
            return
        sejak_diam = None
        _proses(k, *item)


def _proses(k: _Keadaan, aksi_id: str, berkas: str, pesan: str | None) -> None:
    nama = Path(berkas).name
    if pesan is None:
        with k.kunci:  # tunggu satu kiriman selesai dimasukkan agar hitungan sisa tidak terpotong
            sisa = k.antrean.qsize()
        jendela.mulai_tugas(nama, daftar_aksi.SEMUA[aksi_id].label, sisa)
        try:
            hasil = daftar_aksi.jalankan(aksi_id, Path(berkas), jendela.progres)
        except Exception as e:  # satu berkas gagal tidak boleh menghentikan antrean
            pesan = str(e) or type(e).__name__
        else:
            jendela.selesai(list(hasil or []))
            return
    k.gagal += 1
    jendela.galat(f"{nama}: {pesan}")
