"""Jendela progres kecil di pojok kanan bawah, di atas taskbar.

Fungsi publik dipanggil dari thread worker dan hanya menitip kerja ke thread Tk lewat `ui_tk.panggil`.
`tampil()` dibaca antrean untuk tahu kapan proses boleh berhenti; nilainya diubah di sisi pemanggil
(bukan menunggu Tk) supaya timer tutup otomatis yang basi tidak bisa menutup jendela yang baru dipakai lagi.
"""
import ctypes
import subprocess
import threading
import tkinter as tk
from ctypes import wintypes
from pathlib import Path
from tkinter import ttk

from jelma import ui_tk

LEBAR = 360
TUTUP_OTOMATIS_MS = 3000
MAKS_HASIL = 3
MAKS_GALAT = 6
_GAYA_BAR = "Jelma.Horizontal.TProgressbar"

_kunci = threading.Lock()
_gen = 0           # naik setiap ada kabar dari worker; timer tutup hanya berlaku untuk gen-nya sendiri
_tampil = False
_nilai = 0.0
_progres_tertunda = False

# Hanya disentuh di thread Tk.
_w: dict = {}
_galat: list[str] = []
_gaya_siap = False


def tampil() -> bool:
    return _tampil


def mulai_tugas(nama_berkas: str, label_aksi: str, sisa: int) -> None:
    _tandai()
    ui_tk.panggil(lambda: _ui_mulai(nama_berkas, label_aksi, sisa))


def progres(nilai: float) -> None:
    global _nilai, _progres_tertunda
    _nilai = max(0.0, min(1.0, float(nilai)))
    if not _progres_tertunda:  # mesin bisa melapor ratusan kali per detik; cukup satu pembaruan per giliran Tk
        _progres_tertunda = True
        ui_tk.panggil(_ui_progres)


def selesai(hasil: list[Path]) -> None:
    gen = _tandai()
    ui_tk.panggil(lambda: _ui_selesai([Path(p) for p in hasil], gen))


def galat(pesan: str) -> None:
    _tandai()
    ui_tk.panggil(lambda: _ui_galat(pesan))


def _tandai() -> int:
    global _gen, _tampil
    with _kunci:
        _gen += 1
        _tampil = True
        return _gen


def _ui_mulai(nama: str, label: str, sisa: int) -> None:
    w = _bangun()
    w["aktif"] = True
    w["tanda"].config(text="")
    w["nama"].config(text=_pendek(nama))
    w["aksi"].config(text=label)
    w["sisa"].config(text=f"{sisa} berkas lagi" if sisa else "")
    w["bar"]["value"] = 0
    w["tombol"].pack_forget()
    _posisikan()


def _ui_progres() -> None:
    global _progres_tertunda
    _progres_tertunda = False
    if _w:
        _w["bar"]["value"] = _nilai


def _ui_selesai(hasil: list[Path], gen: int) -> None:
    w = _bangun()
    w["aktif"] = False
    w["tanda"].config(text="✓", fg=ui_tk.WARNA["aksen"])
    w["bar"]["value"] = 1.0
    if hasil:
        _baris_hasil(hasil)
    if _galat:
        _tampilkan_tombol()
    else:
        w["top"].after(TUTUP_OTOMATIS_MS, lambda: _tutup_bila(gen))
    _posisikan()


def _ui_galat(pesan: str) -> None:
    w = _bangun()
    if w["aktif"]:  # galat milik tugas yang sedang tampil; galat validasi tidak mengubah baris tugas
        w["aktif"] = False
        w["tanda"].config(text="✗", fg=ui_tk.WARNA["galat"])
    elif not w["nama"].cget("text"):
        w["nama"].config(text="Ada berkas yang gagal")
    _galat.append(pesan)
    if len(_galat) <= MAKS_GALAT:
        _label(w["daftar_galat"], f"✗ {pesan}", ui_tk.WARNA["galat"]).pack(fill="x", anchor="w")
    else:
        w["lebih"].config(text=f"+{len(_galat) - MAKS_GALAT} galat lain")
        w["lebih"].pack(fill="x", anchor="w", padx=14)
    _tampilkan_tombol()
    _posisikan()


def _tutup_bila(gen: int) -> None:
    global _tampil
    with _kunci:
        if gen != _gen or _galat:
            return
        _tampil = False
    _hancurkan()


def _tutup_manual() -> None:
    global _tampil
    with _kunci:
        _tampil = False  # bila worker sedang jalan, kabar berikutnya menyalakan lagi
    _hancurkan()


def _hancurkan() -> None:
    if _w.get("top") is not None:
        _w["top"].destroy()
    _w.clear()
    _galat.clear()


def _bangun() -> dict:
    if _w:
        return _w
    W = ui_tk.WARNA
    top = tk.Toplevel(ui_tk.akar(), bg=W["latar"], highlightthickness=1, highlightbackground=W["garis"])
    top.withdraw()
    top.overrideredirect(True)   # tanpa bingkai dan tanpa tombol taskbar, jadi tidak ada kedip
    top.attributes("-topmost", True)
    _siapkan_gaya(top)

    kepala = tk.Frame(top, bg=W["latar"])
    kepala.pack(fill="x", padx=14, pady=(12, 2))
    tk.Label(kepala, text="Jelma", bg=W["latar"], fg=W["redup"], font=(ui_tk.FONT[0], 9)).pack(side="left")
    sisa = tk.Label(kepala, text="", bg=W["latar"], fg=W["redup"], font=(ui_tk.FONT[0], 9))
    sisa.pack(side="right")

    baris = tk.Frame(top, bg=W["latar"])
    baris.pack(fill="x", padx=14)
    tanda = tk.Label(baris, text="", bg=W["latar"], font=(ui_tk.FONT[0], 11, "bold"))
    tanda.pack(side="right")
    nama = tk.Label(baris, text="", anchor="w", bg=W["latar"], fg=W["teks"], font=(ui_tk.FONT[0], 10, "bold"))
    nama.pack(side="left", fill="x", expand=True)
    aksi = tk.Label(top, text="", anchor="w", bg=W["latar"], fg=W["redup"], font=ui_tk.FONT)
    aksi.pack(fill="x", padx=14)

    bar = ttk.Progressbar(top, style=_GAYA_BAR, maximum=1.0, mode="determinate")
    bar.pack(fill="x", padx=14, pady=(8, 10))

    daftar_hasil = tk.Frame(top, bg=W["latar"])
    daftar_hasil.pack(fill="x", padx=14)
    daftar_galat = tk.Frame(top, bg=W["latar"])
    daftar_galat.pack(fill="x", padx=14)
    lebih = tk.Label(top, text="", anchor="w", bg=W["latar"], fg=W["redup"], font=(ui_tk.FONT[0], 9))
    tombol = tk.Button(top, text="Tutup", command=_tutup_manual, relief="flat", bd=0, cursor="hand2",
                       bg=W["panel"], fg=W["teks"], activebackground=W["garis"], activeforeground=W["teks"],
                       font=ui_tk.FONT, padx=16, pady=4)
    tk.Frame(top, bg=W["latar"], height=6).pack(side="bottom", fill="x")

    _w.update(aktif=False, top=top, sisa=sisa, tanda=tanda, nama=nama, aksi=aksi, bar=bar,
              daftar_hasil=daftar_hasil, daftar_galat=daftar_galat, lebih=lebih, tombol=tombol)
    return _w


def _siapkan_gaya(top: tk.Toplevel) -> None:
    """Tema bawaan Windows (vista) mengabaikan warna progressbar; pinjam elemen dari tema clam saja."""
    global _gaya_siap
    if _gaya_siap:
        return
    W = ui_tk.WARNA
    s = ttk.Style(top)
    s.element_create("Jelma.trough", "from", "clam")
    s.element_create("Jelma.pbar", "from", "clam")
    s.layout(_GAYA_BAR, [("Jelma.trough", {"sticky": "nswe", "children": [
        ("Jelma.pbar", {"side": "left", "sticky": "ns"})]})])
    s.configure(_GAYA_BAR, troughcolor=W["garis"], background=W["aksen"], bordercolor=W["garis"],
                lightcolor=W["aksen"], darkcolor=W["aksen"], thickness=6)
    _gaya_siap = True


def _baris_hasil(hasil: list[Path]) -> None:
    induk = _w["daftar_hasil"]
    lama = induk.winfo_children()
    if len(lama) >= MAKS_HASIL:
        lama[0].destroy()
    teks = f"✓ {_pendek(hasil[0].name, 40)}" + (f"  (+{len(hasil) - 1})" if len(hasil) > 1 else "")
    lbl = _label(induk, teks, ui_tk.WARNA["aksen"])
    lbl.config(cursor="hand2")
    lbl.bind("<Button-1>", lambda _e, p=hasil[0]: _buka_di_explorer(p))
    lbl.pack(fill="x", anchor="w")


def _label(induk: tk.Widget, teks: str, warna: str) -> tk.Label:
    return tk.Label(induk, text=teks, anchor="w", justify="left", wraplength=LEBAR - 32,
                    bg=ui_tk.WARNA["latar"], fg=warna, font=(ui_tk.FONT[0], 9))


def _tampilkan_tombol() -> None:
    _w["tombol"].pack(side="bottom", anchor="e", padx=14, pady=(8, 0))


def _buka_di_explorer(p: Path) -> None:
    # Argumen harus satu string mentah: daftar argumen akan dikutip ulang dan /select, gagal dibaca Explorer.
    subprocess.Popen(f'explorer /select,"{p}"')


def _area_kerja(top: tk.Toplevel) -> tuple[int, int]:
    """Sudut kanan bawah area kerja (layar dikurangi taskbar)."""
    r = wintypes.RECT()
    if ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0):  # SPI_GETWORKAREA
        return r.right, r.bottom
    return top.winfo_screenwidth(), top.winfo_screenheight() - 48


def _posisikan() -> None:
    top = _w["top"]
    top.update_idletasks()
    kanan, bawah = _area_kerja(top)
    tinggi = top.winfo_reqheight()
    top.geometry(f"{LEBAR}x{tinggi}+{kanan - LEBAR - 12}+{bawah - tinggi - 12}")
    top.deiconify()
    top.lift()


def _pendek(teks: str, maks: int = 44) -> str:
    return teks if len(teks) <= maks else teks[: maks - 1] + "…"
