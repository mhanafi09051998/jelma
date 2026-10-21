import hashlib
import io
import json
import time

import pytest

from jelma import __version__, pembaruan, setelan


@pytest.fixture(autouse=True)
def appdata_sementara(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))


def rilis(tag, nama="Jelma-Setup-9.9.9.exe", isi=b"installer", **lain):
    aset = {"name": nama, "size": len(isi), "browser_download_url": "https://contoh/unduh",
            "digest": "sha256:" + hashlib.sha256(isi).hexdigest()}
    return {"tag_name": tag, "draft": False, "prerelease": False, "assets": [aset], **lain}


def palsukan_jaringan(monkeypatch, data_rilis, isi=b"installer"):
    def ambil(url, batas_detik=15):
        return io.BytesIO(json.dumps(data_rilis).encode()) if url == pembaruan.API else io.BytesIO(isi)
    monkeypatch.setattr(pembaruan, "_ambil", ambil)


def test_versi_tuple():
    assert pembaruan.versi_tuple("v1.2.10") == (1, 2, 10)
    assert pembaruan.versi_tuple("1.0.1") > pembaruan.versi_tuple("v1.0.0")


def test_pilih_installer_hanya_versi_lebih_baru():
    assert pembaruan.pilih_installer(rilis(f"v{__version__}")) is None
    assert pembaruan.pilih_installer(rilis("v0.0.1")) is None
    assert pembaruan.pilih_installer(rilis("v99.0.0", prerelease=True)) is None
    assert pembaruan.pilih_installer(rilis("v99.0.0"))["name"] == "Jelma-Setup-9.9.9.exe"


def test_ada_versi_baru_diunduh_dicek_dan_dipasang(monkeypatch, tmp_path):
    monkeypatch.setattr(pembaruan.tempfile, "gettempdir", lambda: str(tmp_path))
    palsukan_jaringan(monkeypatch, rilis("v99.0.0"))
    dipasang = []
    assert pembaruan.cek_sekali(dipasang.append) == "memasang v99.0.0"
    assert dipasang[0].read_bytes() == b"installer"
    assert setelan.muat()["cek_terakhir"] > 0


def test_sha256_tidak_cocok_ditolak(monkeypatch, tmp_path):
    monkeypatch.setattr(pembaruan.tempfile, "gettempdir", lambda: str(tmp_path))
    data = rilis("v99.0.0")
    palsukan_jaringan(monkeypatch, data, isi=b"diubah!!!")
    with pytest.raises(ValueError):
        pembaruan.cek_sekali(lambda p: pytest.fail("tidak boleh dipasang"))
    assert not (tmp_path / "Jelma-Setup-9.9.9.exe").exists()


def test_offline_tidak_mencatat_waktu_cek(monkeypatch):
    def gagal(url, batas_detik=15):
        raise OSError("tidak ada jaringan")
    monkeypatch.setattr(pembaruan, "_ambil", gagal)
    assert pembaruan.cek_sekali(lambda p: None) == "offline"
    assert setelan.muat()["cek_terakhir"] == 0.0


def test_dimatikan_dan_jeda_24_jam(monkeypatch):
    palsukan_jaringan(monkeypatch, rilis("v99.0.0"))
    setelan.simpan({**setelan.muat(), "perbarui_otomatis": False})
    assert pembaruan.cek_sekali(lambda p: None) == "dimatikan"
    setelan.simpan({**setelan.muat(), "perbarui_otomatis": True, "cek_terakhir": time.time()})
    assert pembaruan.cek_sekali(lambda p: None) == "belum 24 jam"
