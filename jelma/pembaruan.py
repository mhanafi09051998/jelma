"""Pembaruan otomatis: saat online, cek rilis terbaru di GitHub paling sering sekali per 24 jam.

Yang dikirim hanya satu permintaan versi ke api.github.com; tidak ada data berkas pengguna.
Bila ada versi baru, installer diunduh ke %TEMP%, dicek ukuran dan SHA256-nya, lalu dipasang diam-diam.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from jelma import __version__, setelan

API = "https://api.github.com/repos/mhanafi09051998/jelma/releases/latest"
JEDA_CEK = 24 * 3600


def versi_tuple(teks: str) -> tuple[int, ...]:
    """"v1.2.10" -> (1, 2, 10); bagian yang bukan angka diabaikan."""
    return tuple(int(b) for b in teks.lstrip("vV").split(".") if b.isdigit())


def pilih_installer(rilis: dict) -> dict | None:
    """Aset Jelma-Setup-*.exe dari data rilis, bila versinya lebih baru dari yang terpasang."""
    if rilis.get("draft") or rilis.get("prerelease"):
        return None
    if versi_tuple(rilis.get("tag_name", "")) <= versi_tuple(__version__):
        return None
    return next((a for a in rilis.get("assets", [])
                 if a.get("name", "").startswith("Jelma-Setup-") and a["name"].endswith(".exe")), None)


def _ambil(url: str, batas_detik: int = 15):
    minta = urllib.request.Request(url, headers={"User-Agent": f"Jelma/{__version__}", "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(minta, timeout=batas_detik)


def unduh(aset: dict, tujuan: Path) -> Path:
    h = hashlib.sha256()
    with _ambil(aset["browser_download_url"], 120) as r, open(tujuan, "wb") as f:
        while blok := r.read(1 << 20):
            h.update(blok)
            f.write(blok)
    if tujuan.stat().st_size != aset.get("size"):
        tujuan.unlink(missing_ok=True)
        raise ValueError("ukuran installer tidak cocok")
    digest = aset.get("digest") or ""
    if digest.startswith("sha256:") and digest[7:] != h.hexdigest():
        tujuan.unlink(missing_ok=True)
        raise ValueError("SHA256 installer tidak cocok")
    return tujuan


def cek_sekali(saat_siap_pasang) -> str:
    """Satu putaran cek. Mengembalikan alasan singkat untuk log; memanggil saat_siap_pasang(path) bila ada pembaruan."""
    data = setelan.muat()
    if not data["perbarui_otomatis"]:
        return "dimatikan"
    if time.time() - data["cek_terakhir"] < JEDA_CEK:
        return "belum 24 jam"
    try:
        with _ambil(API) as r:
            rilis = json.load(r)
    except OSError:
        return "offline"  # coba lagi di putaran berikutnya tanpa mencatat waktu cek
    data["cek_terakhir"] = time.time()
    setelan.simpan(data)
    aset = pilih_installer(rilis)
    if not aset:
        return "sudah terbaru"
    berkas = unduh(aset, Path(tempfile.gettempdir()) / aset["name"])
    saat_siap_pasang(berkas)
    return f"memasang {rilis['tag_name']}"


def pasang(installer: Path) -> None:
    # Installer menutup jelma.exe sendiri (CloseApplications) lalu menyalakan ulang proses latar setelah selesai.
    subprocess.Popen([str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP, close_fds=True)


def mulai(saat_siap_pasang) -> None:
    """Jalankan pengecekan berkala di thread latar; hanya pada versi terpasang (bukan mode pengembangan)."""
    if not getattr(sys, "frozen", False):
        return

    def putar():
        time.sleep(60)  # beri waktu jaringan siap setelah Windows login
        while True:
            try:
                if cek_sekali(saat_siap_pasang).startswith("memasang"):
                    return
            except Exception as e:
                print("pembaruan:", e)
            time.sleep(3600)

    threading.Thread(target=putar, name="pembaruan", daemon=True).start()
