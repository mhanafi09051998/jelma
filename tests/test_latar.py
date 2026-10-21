from pathlib import Path

import pytest

from jelma import daftar_aksi, latar, menu_kursor, pilihan_explorer, setelan


@pytest.mark.parametrize("teks, mods, vk", [
    ("ctrl+alt+j", setelan.MOD_CONTROL | setelan.MOD_ALT, 0x4A),
    ("ctrl+shift+f12", setelan.MOD_CONTROL | setelan.MOD_SHIFT, 0x7B),
    ("alt+win+space", setelan.MOD_WIN | setelan.MOD_ALT, 0x20),
    ("ctrl+alt+shift+win+5", 0xF, 0x35),
    ("alt+pagedown", setelan.MOD_ALT, 0x22),
    ("ctrl+/", setelan.MOD_CONTROL, 0xBF),
])
def test_pintasan_bolak_balik(teks, mods, vk):
    assert setelan.urai_pintasan(teks) == (mods, vk)
    assert setelan.format_pintasan(mods, vk) == teks
    assert setelan.format_pintasan(mods | setelan.MOD_NOREPEAT, vk) == teks


@pytest.mark.parametrize("teks, kanonik", [
    ("Alt + Ctrl + J", "ctrl+alt+j"),
    ("CONTROL+Escape", "ctrl+esc"),
    ("shift+win+PgDn", "shift+win+pagedown"),
])
def test_pintasan_dinormalkan(teks, kanonik):
    assert setelan.format_pintasan(*setelan.urai_pintasan(teks)) == kanonik


@pytest.mark.parametrize("teks", ["", "   ", "j", "ctrl", "ctrl+alt", "ctrl+alt+", "ctrl+j+k",
                                  "ctrl+ctrl+j", "ctrl+alt+zz", "hyper+j", None])
def test_pintasan_tidak_valid(teks):
    with pytest.raises(ValueError):
        setelan.urai_pintasan(teks)


def test_format_tidak_valid():
    with pytest.raises(ValueError):
        setelan.format_pintasan(0, 0x4A)
    with pytest.raises(ValueError):
        setelan.format_pintasan(setelan.MOD_CONTROL, 0xFF)


def test_tampilan():
    assert setelan.tampilan("ctrl+alt+j") == "Ctrl+Alt+J"
    assert setelan.tampilan("shift+f5") == "Shift+F5"


def test_muat_simpan(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert setelan.muat() == setelan.BAWAAN
    setelan.simpan({"pintasan": "ctrl+shift+k", "jeda": True})
    assert setelan.muat() == {"pintasan": "ctrl+shift+k", "jeda": True}
    berkas = tmp_path / "Jelma" / "setelan.json"
    berkas.write_text('{"jeda": "ya", "asing": 1}', encoding="utf-8")
    assert setelan.muat() == setelan.BAWAAN
    berkas.write_text("{rusak", encoding="utf-8")
    assert setelan.muat() == setelan.BAWAAN


def test_teks_dari_tombol():
    ditekan = {0x11, 0x12}
    assert latar.teks_dari_tombol(0x4A, lambda vk: vk in ditekan) == "ctrl+alt+j"
    assert latar.teks_dari_tombol(0x11, lambda vk: vk in ditekan) is None
    assert latar.teks_dari_tombol(0x4A, lambda vk: False) is None
    assert latar.teks_dari_tombol(0x4A, lambda vk: vk == 0x5C) == "win+j"


def test_susun_entri_gambar():
    aksi = daftar_aksi.aksi_bersama([Path("a.png"), Path("b.PNG")])
    entri = menu_kursor.susun_entri(2, aksi)
    assert entri[0] == ("judul", "Jelma · 2 berkas")
    assert entri[1] == ("pemisah",)
    item = [e for e in entri if e[0] == "aksi"]
    assert [e[1] for e in item] == [a.id for a in aksi]
    assert "gambar-ke-png" not in [e[1] for e in item]
    assert entri.count(("pemisah",)) == 1 + sum(1 for a in aksi[1:] if a.pemisah)
    i = next(i for i, e in enumerate(entri) if e[0] == "aksi" and e[1] == "gambar-ke-pdf")
    assert entri[i - 1] == ("pemisah",)


def test_susun_entri_pemisah_di_awal_tidak_ganda():
    aksi = [daftar_aksi.Aksi("x", "X", "m:f", pemisah=True), daftar_aksi.Aksi("y", "Y", "m:f")]
    assert menu_kursor.susun_entri(1, aksi) == [
        ("judul", "Jelma · 1 berkas"), ("pemisah",), ("aksi", "x", "X"), ("aksi", "y", "Y")]


def test_susun_entri_kosong():
    assert menu_kursor.susun_entri(0, []) == [("judul", "Jelma · 0 berkas"), ("pemisah",)]


@pytest.mark.parametrize("hwnd, kelas", [(0, ""), (1234, "Chrome_WidgetWin_1"), (1234, "Notepad")])
def test_explorer_bukan_depan(monkeypatch, hwnd, kelas):
    monkeypatch.setattr(pilihan_explorer.win32gui, "GetForegroundWindow", lambda: hwnd)
    monkeypatch.setattr(pilihan_explorer.win32gui, "GetClassName", lambda _h: kelas)
    dispatch = []
    monkeypatch.setattr(pilihan_explorer.win32com.client, "Dispatch", lambda *a: dispatch.append(a))
    assert pilihan_explorer.berkas_terpilih() == []
    assert dispatch == []


class _Item:
    def __init__(self, path, folder=False, fs=True):
        self.Path, self.IsFolder, self.IsFileSystem = path, folder, fs


class _Dok:
    def SelectedItems(self):
        return [_Item(r"C:\a.png"), _Item(r"C:\folder", folder=True), _Item("::{virtual}", fs=False),
                _Item(r"C:\b.pdf")]


def test_jalur_lewati_folder_dan_virtual():
    assert pilihan_explorer._jalur(_Dok()) == [Path(r"C:\a.png"), Path(r"C:\b.pdf")]
