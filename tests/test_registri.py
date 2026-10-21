import winreg

import pytest

from jelma import daftar_aksi, registri

UJI = r"Software\JelmaUji"
HKCU = winreg.HKEY_CURRENT_USER


@pytest.fixture(autouse=True)
def kunci_uji(monkeypatch):
    monkeypatch.setattr(registri, "BASIS", rf"{UJI}\Classes\SystemFileAssociations")
    monkeypatch.setattr(registri, "RUN", rf"{UJI}\Run")
    monkeypatch.setattr(registri, "_kabari_explorer", lambda: None)
    registri._hapus_pohon(HKCU, UJI)
    yield
    registri._hapus_pohon(HKCU, UJI)


def _nilai(jalur, nama):
    with winreg.OpenKey(HKCU, jalur) as k:
        return winreg.QueryValueEx(k, nama)


def _anak(jalur):
    with winreg.OpenKey(HKCU, jalur) as k:
        return [winreg.EnumKey(k, i) for i in range(winreg.QueryInfoKey(k)[0])]


def _ada(jalur):
    try:
        winreg.OpenKey(HKCU, jalur).Close()
        return True
    except FileNotFoundError:
        return False


def test_pasang_membuat_submenu_lengkap():
    registri.pasang(r"C:\Program Files\Jelma\jelma.exe")
    for exts in daftar_aksi.KELOMPOK.values():
        for ext in exts:
            induk = rf"{registri.BASIS}\.{ext}\shell\Jelma"
            assert _nilai(induk, "MUIVerb") == ("Jelma", winreg.REG_SZ)
            assert _nilai(induk, "Extended") == ("", winreg.REG_SZ)
            assert _nilai(induk, "SubCommands")[0] == ""
            assert _nilai(induk, "MultiSelectModel")[0] == "Player"
            assert _nilai(induk, "Icon")[0] == r"C:\Program Files\Jelma\jelma.exe"
            assert _anak(induk) == ["shell"]


def test_item_menu_urut_pemisah_dan_perintah():
    exe = r"C:\Program Files\Jelma\jelma.exe"
    registri.pasang(exe)
    shell = rf"{registri.BASIS}\.png\shell\Jelma\shell"
    nama = _anak(shell)
    harapan = [a for a in daftar_aksi.aksi_untuk("x.png")]
    assert nama == [f"{i:02d}-{a.id}" for i, a in enumerate(harapan, 1)]
    assert "gambar-ke-png" not in " ".join(nama)  # format sama dengan sumber disembunyikan
    for kunci, aksi in zip(nama, harapan):
        assert _nilai(rf"{shell}\{kunci}", "MUIVerb")[0] == aksi.label
        assert _nilai(rf"{shell}\{kunci}\command", "")[0] == f'"{exe}" {aksi.id} "%1"'
        if aksi.pemisah:
            assert _nilai(rf"{shell}\{kunci}", "CommandFlags") == (0x20, winreg.REG_DWORD)
        else:
            with pytest.raises(FileNotFoundError):
                _nilai(rf"{shell}\{kunci}", "CommandFlags")


def test_pasang_mengaktifkan_mulai_otomatis():
    registri.pasang(r"C:\J\jelma.exe")
    assert registri.mulai_otomatis_aktif()
    assert _nilai(registri.RUN, "Jelma")[0] == r'"C:\J\jelma.exe" --latar'


def test_copot_hanya_menghapus_kunci_jelma():
    lain = rf"{registri.BASIS}\.png\shell\EditLain"
    winreg.CreateKey(HKCU, lain).Close()
    registri.pasang(r"C:\J\jelma.exe")
    registri.copot()
    assert not _ada(rf"{registri.BASIS}\.png\shell\Jelma")
    assert not _ada(rf"{registri.BASIS}\.mp4\shell\Jelma")
    assert _ada(lain)
    assert _ada(rf"{registri.BASIS}\.pdf")
    assert not registri.mulai_otomatis_aktif()


def test_atur_mulai_otomatis_bolak_balik():
    assert not registri.mulai_otomatis_aktif()
    registri.atur_mulai_otomatis(True, r"C:\J\jelma.exe")
    assert registri.mulai_otomatis_aktif()
    registri.atur_mulai_otomatis(False)
    assert not registri.mulai_otomatis_aktif()
    registri.atur_mulai_otomatis(False)  # menghapus yang sudah tidak ada tidak galat


def test_perintah_mode_pengembangan_tidak_bergantung_cwd():
    awal = registri.perintah()
    assert awal.startswith('"') and "pythonw" in awal.lower()
    assert "sys.path.insert(0,r'" in awal and "from jelma.main import main" in awal


def test_perintah_mode_pengembangan_jalan_dari_folder_lain(tmp_path):
    import subprocess

    from jelma import __version__
    baris = registri.perintah().replace("pythonw.exe", "python.exe") + " --versi"
    keluar = subprocess.run(baris, cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert keluar.stdout.strip() == __version__
