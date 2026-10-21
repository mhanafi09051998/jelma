"""Berkas yang sedang dipilih di jendela Explorer (atau Desktop) yang aktif di depan.

Explorer Windows 11 bertab: semua tab berbagi satu HWND puncak. Tab aktif dikenali dari anak
`ShellTabWindowClass` yang terlihat paling atas; tiap jendela shell dicocokkan lewat
IServiceProvider -> IShellBrowser.GetWindow(), yang mengembalikan HWND tab miliknya.
"""
from pathlib import Path

import pythoncom
import win32com.client
import win32gui
from win32com.shell import shell

KELAS_EXPLORER = {"CabinetWClass", "ExploreWClass"}
KELAS_DESKTOP = {"Progman", "WorkerW"}
_SWC_DESKTOP, _SWFO_NEEDDISPATCH = 8, 1


def _tab_aktif(hwnd: int) -> int | None:
    """HWND tab yang terlihat; EnumChildWindows berjalan urut z-order, jadi yang pertama paling depan."""
    tab: list[int] = []

    def kumpul(h, _):
        if win32gui.GetClassName(h) == "ShellTabWindowClass" and win32gui.IsWindowVisible(h):
            tab.append(h)
        return True

    try:
        win32gui.EnumChildWindows(hwnd, kumpul, None)
    except win32gui.error:
        pass
    return tab[0] if tab else None


def _hwnd_tab(jendela) -> int | None:
    try:
        sp = jendela._oleobj_.QueryInterface(pythoncom.IID_IServiceProvider)
        browser = sp.QueryService(shell.SID_STopLevelBrowser, shell.IID_IShellBrowser)
        return browser.GetWindow()
    except pythoncom.com_error:
        return None


def _jendela_explorer(semua, hwnd: int):
    calon = []
    for i in range(semua.Count):
        try:
            w = semua.Item(i)
            if w is not None and w.HWND == hwnd:
                calon.append(w)
        except pythoncom.com_error:
            continue  # jendela sedang ditutup
    if len(calon) <= 1:
        return calon[0] if calon else None
    aktif = _tab_aktif(hwnd)
    return next((w for w in calon if _hwnd_tab(w) == aktif), calon[0])


def _jalur(dokumen) -> list[Path]:
    hasil = []
    for item in dokumen.SelectedItems():
        if item.IsFolder or not item.IsFileSystem:
            continue  # folder & arsip zip (IsFolder) dan objek virtual dilewati
        hasil.append(Path(item.Path))
    return hasil


def berkas_terpilih() -> list[Path]:
    """Berkas terpilih di jendela depan; [] bila jendela depan bukan Explorer/Desktop. Aman dari thread mana pun."""
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return []
    kelas = win32gui.GetClassName(hwnd)
    if kelas not in KELAS_EXPLORER and kelas not in KELAS_DESKTOP:
        return []
    pythoncom.CoInitialize()  # hitungan ref per thread; panggilan berulang aman
    try:
        semua = win32com.client.Dispatch("Shell.Application").Windows()
        if kelas in KELAS_DESKTOP:
            jendela = semua.FindWindowSW(0, 0, _SWC_DESKTOP, 0, _SWFO_NEEDDISPATCH)
        else:
            jendela = _jendela_explorer(semua, hwnd)
        if jendela is None:
            return []
        return _jalur(jendela.Document)
    except (pythoncom.com_error, AttributeError):
        return []
