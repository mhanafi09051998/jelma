"""Menu aksi dan tooltip yang muncul di posisi kursor. Semua fungsi publik wajib dipanggil di thread Tk
(lewat `ui_tk.panggil`).

Quirk Windows: tk_popup dari proses yang tidak di depan muncul di belakang jendela lain dan tidak
tertutup saat klik di luar. Solusinya jendela bantu 1x1 transparan topmost di kursor yang dipaksa ke
depan (AttachThreadInput + SetForegroundWindow) sebelum menu dibuka.
"""
import tkinter as tk
from typing import Callable

import win32api
import win32gui
import win32process

from jelma import ui_tk

GAYA_MENU = {"bg": "#151824", "fg": "#e5e7eb", "activebackground": "#22c55e", "activeforeground": "#0a0c13",
             "disabledforeground": "#9ca3af", "relief": "flat", "bd": 0, "font": ui_tk.FONT}


def susun_entri(jumlah: int, aksi_list) -> list[tuple]:
    """Daftar entri menu, murni tanpa Tk: ("judul", teks) | ("pemisah",) | ("aksi", id, label)."""
    entri: list[tuple] = [("judul", f"Jelma · {jumlah} berkas"), ("pemisah",)]
    for i, aksi in enumerate(aksi_list):
        if aksi.pemisah and i > 0:
            entri.append(("pemisah",))
        entri.append(("aksi", aksi.id, aksi.label))
    return entri


def _paksa_depan(hwnd: int) -> None:
    """SetForegroundWindow ditolak Windows bila thread kita tidak berbagi input dengan jendela depan."""
    depan = win32gui.GetForegroundWindow()
    t_depan = win32process.GetWindowThreadProcessId(depan)[0] if depan else 0
    t_ini = win32api.GetCurrentThreadId()
    nempel = bool(t_depan) and t_depan != t_ini
    try:
        if nempel:
            win32process.AttachThreadInput(t_ini, t_depan, True)
        win32gui.SetForegroundWindow(hwnd)
    except win32gui.error:
        pass
    finally:
        if nempel:
            win32process.AttachThreadInput(t_ini, t_depan, False)


def _jendela_bantu(x: int, y: int) -> tk.Toplevel:
    bantu = tk.Toplevel(ui_tk.akar())
    bantu.overrideredirect(True)
    bantu.attributes("-topmost", True)
    bantu.attributes("-alpha", 0.0)
    bantu.geometry(f"1x1+{x}+{y}")
    bantu.update_idletasks()
    _paksa_depan(int(bantu.wm_frame(), 16))
    bantu.focus_force()
    return bantu


def tampilkan(paths, aksi_list, saat_dipilih: Callable[[str], None]) -> None:
    x, y = win32api.GetCursorPos()
    bantu = _jendela_bantu(x, y)
    menu = tk.Menu(ui_tk.akar(), tearoff=False, **GAYA_MENU)
    for entri in susun_entri(len(paths), aksi_list):
        if entri[0] == "judul":
            menu.add_command(label=entri[1], state="disabled")
        elif entri[0] == "pemisah":
            menu.add_separator()
        else:
            menu.add_command(label=entri[2], command=lambda aid=entri[1]: saat_dipilih(aid))
    try:
        menu.tk_popup(x, y)
    finally:
        menu.grab_release()
        # perintah menu dikirim setelah tk_popup kembali; hancurkan sesudahnya
        ui_tk.akar().after(200, lambda: (menu.destroy(), bantu.destroy()))


def tooltip(pesan: str, durasi_ms: int = 2000) -> None:
    x, y = win32api.GetCursorPos()
    tip = tk.Toplevel(ui_tk.akar())
    tip.overrideredirect(True)
    tip.attributes("-topmost", True)
    tk.Label(tip, text=pesan, bg=ui_tk.WARNA["panel"], fg=ui_tk.WARNA["teks"], font=ui_tk.FONT,
             padx=12, pady=6, highlightthickness=1, highlightbackground=ui_tk.WARNA["garis"]).pack()
    tip.geometry(f"+{x + 16}+{y + 20}")
    tip.after(durasi_ms, tip.destroy)
