"""Mode latar (`jelma --latar`): ikon tray + pintasan keyboard global yang membuka menu aksi di kursor.

Thread: utama = Tk; pystray punya thread sendiri; pintasan = thread dengan loop GetMessageW sendiri
karena RegisterHotKey(NULL, ...) mengirim WM_HOTKEY ke antrean pesan thread pendaftarnya.
"""
import ctypes
import threading
import tkinter as tk
from ctypes import wintypes

import pystray
import win32api

from jelma import antrean, daftar_aksi, ikon, menu_kursor, pembaruan, pilihan_explorer, registri, setelan, ui_tk

WM_HOTKEY, WM_QUIT, WM_APP = 0x0312, 0x0012, 0x8000
WM_GANTI_PINTASAN = WM_APP + 1
ID_PINTASAN = 1

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
_user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
_user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT,
                                 wintypes.UINT]
_user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
_ASFW_ANY = 0xFFFFFFFF

_setelan = setelan.muat()


def _tooltip(pesan: str) -> None:
    ui_tk.panggil(lambda: menu_kursor.tooltip(pesan))


def _saat_pintasan() -> None:
    if _setelan["jeda"]:
        return
    paths = pilihan_explorer.berkas_terpilih()
    if not paths:
        _tooltip("Pilih file di Explorer dulu")
        return
    aksi = daftar_aksi.aksi_bersama(paths)
    if not aksi:
        _tooltip("Format file ini belum didukung")
        return
    _user32.AllowSetForegroundWindow(_ASFW_ANY)  # hak "input terakhir" milik thread ini, bagikan ke thread Tk
    pilih = lambda aid: antrean.tambah([(aid, str(p)) for p in paths])  # noqa: E731
    ui_tk.panggil(lambda: menu_kursor.tampilkan(paths, aksi, saat_dipilih=pilih))


class Pintasan(threading.Thread):
    def __init__(self, teks: str):
        super().__init__(name="jelma-pintasan", daemon=True)
        self.teks = teks
        self._tid = 0
        self._siap = threading.Event()

    def _daftar(self) -> None:
        try:
            mods, vk = setelan.urai_pintasan(self.teks)
        except ValueError:
            _tooltip(f"Pintasan tidak valid: {self.teks}")
            return
        if not _user32.RegisterHotKey(None, ID_PINTASAN, mods | setelan.MOD_NOREPEAT, vk):
            _tooltip(f"{setelan.tampilan(self.teks)} sudah dipakai aplikasi lain")

    def run(self) -> None:
        import pythoncom
        pythoncom.CoInitialize()
        msg = wintypes.MSG()
        _user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # paksa antrean pesan thread dibuat
        self._tid = _kernel32.GetCurrentThreadId()
        self._daftar()
        self._siap.set()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and msg.wParam == ID_PINTASAN:
                try:
                    _saat_pintasan()
                except Exception as e:  # satu tekan gagal tidak boleh mematikan thread pintasan
                    print("latar:", e)
            elif msg.message == WM_GANTI_PINTASAN:
                _user32.UnregisterHotKey(None, ID_PINTASAN)
                self._daftar()
        _user32.UnregisterHotKey(None, ID_PINTASAN)

    def ganti(self, teks: str) -> None:
        self.teks = teks
        self._siap.wait(2)
        _user32.PostThreadMessageW(self._tid, WM_GANTI_PINTASAN, 0, 0)

    def berhenti(self) -> None:
        self._siap.wait(2)
        _user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)


def teks_dari_tombol(vk: int, tekan) -> str | None:
    """Kombinasi dari keycode Tk (di Windows = virtual-key) dan status modifier; None bila belum lengkap."""
    if vk in setelan.VK_MODIFIER:
        return None
    mods = 0
    for vks, mod in (((0x11,), setelan.MOD_CONTROL), ((0x12,), setelan.MOD_ALT),
                     ((0x10,), setelan.MOD_SHIFT), ((0x5B, 0x5C), setelan.MOD_WIN)):
        if any(tekan(v) for v in vks):
            mods |= mod
    try:
        return setelan.format_pintasan(mods, vk)
    except ValueError:
        return None


def _bilah_gelap(jendela: tk.Toplevel) -> None:
    """Bilah judul gelap (DWMWA_USE_IMMERSIVE_DARK_MODE = 20); diabaikan bila Windows tidak mendukung."""
    nilai = ctypes.c_int(1)
    hwnd = int(jendela.wm_frame(), 16)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(nilai), ctypes.sizeof(nilai))


def _dialog_pintasan(pintasan: Pintasan) -> None:
    w = ui_tk.WARNA
    dlg = tk.Toplevel(ui_tk.akar(), bg=w["latar"], padx=20, pady=16)
    dlg.title("Ganti pintasan Jelma")
    dlg.resizable(False, False)
    dlg.attributes("-topmost", True)
    try:
        dlg.iconbitmap(str(ikon.jalur_ico()))
    except tk.TclError:
        pass
    hasil = {"teks": None}
    tk.Label(dlg, text="Tekan kombinasi tombol baru", bg=w["latar"], fg=w["redup"], font=ui_tk.FONT).pack()
    tampil = tk.Label(dlg, text=setelan.tampilan(_setelan["pintasan"]), bg=w["panel"], fg=w["teks"],
                      font=(ui_tk.FONT[0], 16, "bold"), width=18, pady=10)
    tampil.pack(pady=12)
    info = tk.Label(dlg, text="Wajib pakai Ctrl, Alt, Shift, atau Win", bg=w["latar"], fg=w["redup"],
                    font=(ui_tk.FONT[0], 9))
    info.pack()

    def tekan(e):
        teks = teks_dari_tombol(e.keycode, lambda vk: win32api.GetKeyState(vk) < 0)
        if teks:
            hasil["teks"] = teks
            tampil.config(text=setelan.tampilan(teks), fg=w["aksen"])
            info.config(text="Klik Simpan untuk memakai", fg=w["redup"])
        elif e.keycode not in setelan.VK_MODIFIER:
            info.config(text="Kombinasi tidak didukung", fg=w["galat"])
        return "break"

    def simpan():
        if hasil["teks"]:
            _setelan["pintasan"] = hasil["teks"]
            setelan.simpan(_setelan)
            pintasan.ganti(hasil["teks"])
        dlg.destroy()

    baris = tk.Frame(dlg, bg=w["latar"])
    baris.pack(pady=(14, 0), fill="x")
    gaya = {"font": ui_tk.FONT, "relief": "flat", "bd": 0, "padx": 14, "pady": 4, "takefocus": False}
    tk.Button(baris, text="Batal", command=dlg.destroy, bg=w["panel"], fg=w["teks"],
              activebackground=w["garis"], activeforeground=w["teks"], **gaya).pack(side="right")
    tk.Button(baris, text="Simpan", command=simpan, bg=w["aksen"], fg="#0a0c13",
              activebackground="#16a34a", activeforeground="#0a0c13", **gaya).pack(side="right", padx=(0, 8))
    dlg.bind("<KeyPress>", tekan)
    dlg.update_idletasks()
    _bilah_gelap(dlg)
    x, y = win32api.GetCursorPos()
    dlg.geometry(f"+{max(0, x - dlg.winfo_width() // 2)}+{max(0, y - dlg.winfo_height() // 2)}")
    dlg.focus_force()


def _menu_tray(pintasan: Pintasan) -> pystray.Menu:
    def jeda(_icon, _item):
        _setelan["jeda"] = not _setelan["jeda"]
        setelan.simpan(_setelan)

    def mulai_otomatis(_icon, _item):
        try:
            registri.atur_mulai_otomatis(not registri.mulai_otomatis_aktif())
        except OSError as e:
            _tooltip(f"Gagal mengubah mulai otomatis: {e}")

    def keluar(icon, _item):
        icon.stop()
        pintasan.berhenti()
        ui_tk.berhenti()

    def perbarui(_icon, _item):
        _setelan["perbarui_otomatis"] = not _setelan["perbarui_otomatis"]
        setelan.simpan({**setelan.muat(), "perbarui_otomatis": _setelan["perbarui_otomatis"]})

    return pystray.Menu(
        pystray.MenuItem("Jeda pintasan", jeda, checked=lambda _i: _setelan["jeda"]),
        pystray.MenuItem(lambda _i: f"Ganti pintasan ({setelan.tampilan(_setelan['pintasan'])})…",
                         lambda: ui_tk.panggil(lambda: _dialog_pintasan(pintasan))),
        pystray.MenuItem("Jalan saat Windows mulai", mulai_otomatis,
                         checked=lambda _i: registri.mulai_otomatis_aktif()),
        pystray.MenuItem("Perbarui otomatis", perbarui, checked=lambda _i: _setelan["perbarui_otomatis"]),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Keluar", keluar),
    )


def main() -> int:
    if not antrean.mulai_server(tetap_hidup=True):
        return 0  # instance latar lain sudah memegang pipe
    ui_tk.akar()
    pintasan = Pintasan(_setelan["pintasan"])
    pintasan.start()
    icon = pystray.Icon("Jelma", ikon.gambar_tray(), "Jelma", _menu_tray(pintasan))
    icon.run_detached()

    def pasang_pembaruan(installer):
        pembaruan.pasang(installer)
        icon.stop()
        pintasan.berhenti()
        ui_tk.berhenti()

    pembaruan.mulai(pasang_pembaruan)
    ui_tk.jalankan_loop()
    return 0
