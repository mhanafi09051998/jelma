"""Menu klik kanan dan mulai otomatis lewat HKCU (tanpa hak admin).

Menu dipasang di SystemFileAssociations\\.<ext>\\shell\\Jelma sebagai submenu bertingkat, hanya tampil
saat Shift+klik kanan (nilai Extended). Kunci ekstensi induk milik Windows/aplikasi lain tidak disentuh.

Mode pengembangan (tidak dibekukan): perintah memakai pythonw.exe dengan `-c` yang menambahkan akar
repo ke sys.path, karena Explorer menjalankan verba dengan cwd = folder berkas sehingga `-m jelma.main`
tidak akan menemukan paket:
    "<pythonw.exe>" -c "import sys;sys.path.insert(0,r'<repo>');from jelma.main import main;sys.exit(main())" <argumen>
"""
import ctypes
import sys
import winreg
from pathlib import Path

from jelma import daftar_aksi

BASIS = r"Software\Classes\SystemFileAssociations"
RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
NAMA = "Jelma"
ECF_SEPARATORBEFORE = 0x20


def perintah(exe: str | None = None) -> str:
    """Awalan baris perintah (sudah dikutip) untuk menjalankan Jelma."""
    if exe:
        return f'"{exe}"'
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    repo = Path(__file__).resolve().parent.parent
    kode = f"import sys;sys.path.insert(0,r'{repo}');from jelma.main import main;sys.exit(main())"
    return f'"{_pythonw()}" -c "{kode}"'


def ikon(exe: str | None = None) -> str:
    if exe:
        return exe
    return sys.executable if getattr(sys, "frozen", False) else _pythonw()


def pasang(exe: str | None = None) -> None:
    awal, gambar = perintah(exe), ikon(exe)
    for kel, exts in daftar_aksi.KELOMPOK.items():
        for ext in exts:
            _pasang_ext(ext, daftar_aksi.AKSI_PER_KELOMPOK[kel], awal, gambar)
    atur_mulai_otomatis(True, exe)
    _kabari_explorer()


def copot() -> None:
    for exts in daftar_aksi.KELOMPOK.values():
        for ext in exts:
            _hapus_pohon(winreg.HKEY_CURRENT_USER, _kunci_menu(ext))
    atur_mulai_otomatis(False)
    _kabari_explorer()


def atur_mulai_otomatis(aktif: bool, exe: str | None = None) -> None:
    if aktif:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, NAMA, 0, winreg.REG_SZ, f"{perintah(exe)} --latar")
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, NAMA)
    except FileNotFoundError:
        pass


def mulai_otomatis_aktif() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN) as k:
            winreg.QueryValueEx(k, NAMA)
        return True
    except FileNotFoundError:
        return False


def _kunci_menu(ext: str) -> str:
    return rf"{BASIS}\.{ext}\shell\{NAMA}"


def _pasang_ext(ext: str, daftar: list, awal: str, gambar: str) -> None:
    induk = _kunci_menu(ext)
    _hapus_pohon(winreg.HKEY_CURRENT_USER, induk)  # buang item lama bila katalog berubah
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, induk) as k:
        winreg.SetValueEx(k, "MUIVerb", 0, winreg.REG_SZ, NAMA)
        winreg.SetValueEx(k, "Extended", 0, winreg.REG_SZ, "")
        winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, gambar)
        winreg.SetValueEx(k, "SubCommands", 0, winreg.REG_SZ, "")
        winreg.SetValueEx(k, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
    sama = {"jpeg": "jpg", "tif": "tiff", "heif": "heic"}.get(ext, ext)
    urutan = [a for a in daftar if a.format_tujuan != sama]
    for i, aksi in enumerate(urutan, 1):
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{induk}\shell\{i:02d}-{aksi.id}") as k:
            winreg.SetValueEx(k, "MUIVerb", 0, winreg.REG_SZ, aksi.label)
            # Model "Player" juga di verba anak: verba inilah yang dipanggil, tanpa ini Explorer membatasi 15 berkas.
            winreg.SetValueEx(k, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
            if aksi.pemisah:
                winreg.SetValueEx(k, "CommandFlags", 0, winreg.REG_DWORD, ECF_SEPARATORBEFORE)
            with winreg.CreateKey(k, "command") as c:
                winreg.SetValueEx(c, "", 0, winreg.REG_SZ, f'{awal} {aksi.id} "%1"')


def _hapus_pohon(akar, jalur: str) -> None:
    """DeleteKey hanya bisa menghapus kunci tanpa anak, jadi kosongkan dari bawah."""
    try:
        with winreg.OpenKey(akar, jalur, 0, winreg.KEY_READ | winreg.KEY_WRITE) as k:
            while True:
                try:
                    anak = winreg.EnumKey(k, 0)
                except OSError:
                    break
                _hapus_pohon(akar, rf"{jalur}\{anak}")
        winreg.DeleteKey(akar, jalur)
    except FileNotFoundError:
        pass


def _pythonw() -> str:
    calon = Path(sys.executable).with_name("pythonw.exe")
    return str(calon if calon.exists() else sys.executable)


def _kabari_explorer() -> None:
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)  # SHCNE_ASSOCCHANGED, SHCNF_IDLIST
