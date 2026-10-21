"""Satu akar Tk di thread utama; modul lain (jendela progres, menu kursor) menitip kerja lewat `panggil`.

Tk tidak aman lintas thread, jadi pipe server, worker, tray, dan pintasan hanya boleh menyentuh UI lewat sini.
"""
import queue
import tkinter as tk

WARNA = {"latar": "#0e111a", "panel": "#151824", "garis": "#262b3d", "teks": "#e5e7eb",
         "redup": "#9ca3af", "aksen": "#22c55e", "galat": "#ef4444"}
FONT = ("Segoe UI", 10)

_akar: tk.Tk | None = None
_antrean: "queue.Queue" = queue.Queue()


def akar() -> tk.Tk:
    global _akar
    if _akar is None:
        _akar = tk.Tk()
        _akar.withdraw()
        _akar.after(50, _kuras)
    return _akar


def _kuras():
    while True:
        try:
            fn = _antrean.get_nowait()
        except queue.Empty:
            break
        try:
            fn()
        except Exception as e:  # satu callback UI gagal tidak boleh mematikan loop
            print("ui_tk:", e)
    _akar.after(50, _kuras)


def panggil(fn) -> None:
    """Aman dari thread mana pun: jalankan `fn()` di thread Tk."""
    _antrean.put(fn)


def jalankan_loop() -> None:
    akar().mainloop()


def berhenti() -> None:
    panggil(lambda: _akar.quit())
