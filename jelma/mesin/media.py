"""Konversi video & audio lewat ffmpeg."""
import json
import subprocess
import threading
from collections import deque
from pathlib import Path
from typing import Callable

from jelma import keluaran
from jelma.mesin import TANPA_JENDELA, biner

GENAP = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
H264 = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf", GENAP]
# vp9 bawaan sangat lambat; cpu-used 4 + row-mt menjaga kecepatan wajar untuk pemakaian desktop.
VP9 = ["-c:v", "libvpx-vp9", "-crf", "33", "-b:v", "0", "-deadline", "good", "-cpu-used", "4",
       "-row-mt", "1", "-pix_fmt", "yuv420p", "-vf", GENAP]
FASTSTART = ["-movflags", "+faststart"]

VIDEO = {
    "mp4": [*H264, "-crf", "23", "-preset", "medium", "-c:a", "aac", "-b:a", "160k", *FASTSTART],
    "mov": [*H264, "-crf", "23", "-preset", "medium", "-c:a", "aac", "-b:a", "160k", *FASTSTART],
    "mkv": [*H264, "-crf", "23", "-preset", "medium", "-c:a", "aac", "-b:a", "160k"],
    "webm": [*VP9, "-c:a", "libopus", "-b:a", "128k"],
}

AUDIO = {
    "mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    "wav": ["-c:a", "pcm_s16le"],
    "ogg": ["-c:a", "libvorbis", "-q:a", "5"],
    "flac": ["-c:a", "flac"],
    "m4a": ["-c:a", "aac", "-b:a", "192k"],
    "opus": ["-c:a", "libopus", "-b:a", "128k"],
}
# Wadah yang sanggup menyimpan sampul album (attached_pic) jpg/png.
BISA_SAMPUL = {"mp3", "flac", "m4a"}

Lapor = Callable[[float], None]


def _probe(sumber: Path) -> dict:
    hasil = subprocess.run(
        [biner("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", f"file:{sumber}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=TANPA_JENDELA,
    )
    if hasil.returncode != 0:
        raise RuntimeError(f"Berkas tidak bisa dibaca ffprobe: {hasil.stderr.strip()[-300:]}")
    return json.loads(hasil.stdout or "{}")


def _durasi(info: dict) -> float:
    try:
        return float(info.get("format", {}).get("duration", 0))
    except ValueError:
        return 0.0


def _punya_audio(info: dict) -> bool:
    return any(s.get("codec_type") == "audio" for s in info.get("streams", []))


def _punya_sampul(info: dict) -> bool:
    return any(
        s.get("codec_type") == "video" and s.get("disposition", {}).get("attached_pic")
        and s.get("codec_name") in ("mjpeg", "png")
        for s in info.get("streams", [])
    )


def _jalankan(sumber: Path, tujuan: Path, argumen: list[str], lapor: Lapor, durasi: float) -> list[Path]:
    """Jalankan ffmpeg dengan laporan progres; hapus hasil setengah jadi bila gagal."""
    perintah = [
        biner("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
        "-i", f"file:{sumber}", *argumen, "-progress", "pipe:1", "-nostats", f"file:{tujuan}",
    ]
    galat: deque[str] = deque(maxlen=50)
    proses = subprocess.Popen(
        perintah, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace", creationflags=TANPA_JENDELA,
    )
    # stderr dibaca di utas terpisah supaya pipa tidak penuh dan ffmpeg macet.
    pembaca = threading.Thread(target=lambda: galat.extend(b.rstrip() for b in proses.stderr), daemon=True)
    pembaca.start()
    terakhir = 0.0
    try:
        for baris in proses.stdout:
            kunci, _, nilai = baris.strip().partition("=")
            if kunci == "out_time_us" and durasi > 0 and nilai.lstrip("-").isdigit():
                p = min(max(int(nilai) / 1_000_000 / durasi, 0.0), 1.0)
                if p > terakhir:
                    terakhir = p
                    lapor(p)
        kode = proses.wait()
        pembaca.join(timeout=5)
    except BaseException:
        proses.kill()
        proses.wait()
        tujuan.unlink(missing_ok=True)
        raise
    if kode != 0:
        tujuan.unlink(missing_ok=True)
        pesan = [b for b in galat if b.strip()][-5:]
        raise RuntimeError("ffmpeg gagal:\n" + ("\n".join(pesan) or f"kode keluar {kode}"))
    if terakhir < 1.0:
        lapor(1.0)
    return [tujuan]


def video_ke_format(sumber: Path, lapor: Lapor, format: str) -> list[Path]:
    fmt = format.lower()
    if fmt not in VIDEO:
        raise ValueError(f"Format video tidak didukung: {format}")
    info = _probe(sumber)
    tujuan = keluaran.tujuan(sumber, fmt)
    return _jalankan(sumber, tujuan, ["-sn", "-dn", *VIDEO[fmt]], lapor, _durasi(info))


def video_ke_gif(sumber: Path, lapor: Lapor) -> list[Path]:
    # Palet dua tahap dalam satu graf: warna GIF jauh lebih bersih daripada palet bawaan.
    graf = "fps=12,scale='min(640,iw)':-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse"
    info = _probe(sumber)
    tujuan = keluaran.tujuan(sumber, "gif")
    return _jalankan(sumber, tujuan, ["-vf", graf, "-an", "-sn", "-loop", "0"], lapor, _durasi(info))


def ambil_audio(sumber: Path, lapor: Lapor, format: str = "mp3") -> list[Path]:
    fmt = format.lower()
    if fmt not in AUDIO:
        raise ValueError(f"Format audio tidak didukung: {format}")
    info = _probe(sumber)
    if not _punya_audio(info):
        raise RuntimeError("Video tidak punya trek audio")
    tujuan = keluaran.tujuan(sumber, fmt)
    return _jalankan(sumber, tujuan, ["-map", "0:a:0", "-vn", "-sn", "-dn", *AUDIO[fmt]], lapor, _durasi(info))


def kompres_video(sumber: Path, lapor: Lapor) -> list[Path]:
    asal = Path(sumber).suffix.lstrip(".").lower()
    fmt = asal if asal in ("mp4", "mov", "mkv") else "mp4"
    argumen = [*H264, "-crf", "28", "-preset", "slow", "-c:a", "aac", "-b:a", "128k"]
    if fmt != "mkv":
        argumen += FASTSTART
    info = _probe(sumber)
    tujuan = keluaran.tujuan(sumber, fmt, " (kompres)")
    return _jalankan(sumber, tujuan, ["-sn", "-dn", *argumen], lapor, _durasi(info))


def audio_ke_format(sumber: Path, lapor: Lapor, format: str) -> list[Path]:
    fmt = format.lower()
    if fmt not in AUDIO:
        raise ValueError(f"Format audio tidak didukung: {format}")
    info = _probe(sumber)
    if not _punya_audio(info):
        raise RuntimeError("Berkas tidak punya trek audio")
    if fmt in BISA_SAMPUL and _punya_sampul(info):
        peta = ["-map", "0:a:0", "-map", "0:v:0", "-c:v", "copy", "-disposition:v:0", "attached_pic"]
    else:
        peta = ["-map", "0:a:0", "-vn"]
    tujuan = keluaran.tujuan(sumber, fmt)
    return _jalankan(sumber, tujuan, [*peta, "-sn", "-dn", *AUDIO[fmt]], lapor, _durasi(info))
