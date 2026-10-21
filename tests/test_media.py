import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from jelma.mesin import TANPA_JENDELA, biner
from jelma.mesin import media


def _ffmpeg(*argumen: str) -> None:
    subprocess.run([biner("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *argumen],
                   check=True, creationflags=TANPA_JENDELA)


def _probe(path: Path) -> dict:
    keluar = subprocess.run([biner("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json",
                             str(path)], capture_output=True, text=True, check=True, creationflags=TANPA_JENDELA)
    return json.loads(keluar.stdout)


def _codec(info: dict, jenis: str) -> list[str]:
    return [s["codec_name"] for s in info["streams"] if s["codec_type"] == jenis]


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Perekam:
    def __init__(self):
        self.nilai: list[float] = []

    def __call__(self, p: float) -> None:
        self.nilai.append(p)

    def periksa(self):
        assert self.nilai, "progres tidak pernah dilaporkan"
        assert all(0.0 <= p <= 1.0 for p in self.nilai)
        assert self.nilai == sorted(self.nilai), "progres tidak monoton"
        assert self.nilai[-1] == pytest.approx(1.0, abs=0.01)


@pytest.fixture(scope="module")
def bahan(tmp_path_factory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("media")
    video = d / "klip.mp4"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=25",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(video))
    bisu = d / "bisu.mp4"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=duration=2:size=321x241:rate=25",
            "-c:v", "libx264", "-pix_fmt", "yuv444p", str(bisu))
    avi = d / "lama.avi"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=duration=1:size=160x120:rate=25",
            "-f", "lavfi", "-i", "sine=duration=1", "-c:v", "mpeg4", "-c:a", "mp3", "-shortest", str(avi))
    wav = d / "nada.wav"
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=2", str(wav))
    sampul = d / "sampul.png"
    _ffmpeg("-f", "lavfi", "-i", "color=red:size=64x64", "-frames:v", "1", str(sampul))
    lagu = d / "lagu.mp3"
    _ffmpeg("-i", str(wav), "-i", str(sampul), "-map", "0:a", "-map", "1:v", "-c:a", "libmp3lame",
            "-c:v", "png", "-disposition:v", "attached_pic", str(lagu))
    return {"video": video, "bisu": bisu, "avi": avi, "wav": wav, "lagu": lagu}


@pytest.fixture
def salin(bahan, tmp_path):
    """Salinan bahan di folder sendiri supaya hasil antar-tes tidak bertabrakan."""
    def _salin(kunci: str) -> Path:
        tujuan = tmp_path / bahan[kunci].name
        tujuan.write_bytes(bahan[kunci].read_bytes())
        return tujuan
    return _salin


VIDEO_HARAP = {
    "mp4": ("h264", "aac", "mov,mp4"),
    "mkv": ("h264", "aac", "matroska"),
    "webm": ("vp9", "opus", "webm"),
    "mov": ("h264", "aac", "mov,mp4"),
}


@pytest.mark.parametrize("fmt", list(VIDEO_HARAP))
def test_video_ke_format(salin, fmt):
    sumber = salin("video")
    sebelum = _hash(sumber)
    lapor = Perekam()
    hasil = media.video_ke_format(sumber, lapor, format=fmt)
    assert len(hasil) == 1 and hasil[0].suffix == f".{fmt}" and hasil[0].parent == sumber.parent
    info = _probe(hasil[0])
    v, a, wadah = VIDEO_HARAP[fmt]
    assert _codec(info, "video") == [v]
    assert _codec(info, "audio") == [a]
    assert wadah in info["format"]["format_name"]
    assert float(info["format"]["duration"]) == pytest.approx(2.0, abs=0.3)
    lapor.periksa()
    assert _hash(sumber) == sebelum


def test_video_mp4_ke_mp4_tidak_menimpa(salin):
    sumber = salin("video")
    hasil = media.video_ke_format(sumber, lambda _p: None, format="mp4")
    assert hasil[0].name == "klip (1).mp4"


def test_dimensi_ganjil_jadi_genap(salin):
    hasil = media.video_ke_format(salin("bisu"), lambda _p: None, format="mp4")
    info = _probe(hasil[0])
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (320, 240)
    assert _codec(info, "audio") == []


def test_video_ke_gif(salin):
    sumber = salin("video")
    lapor = Perekam()
    hasil = media.video_ke_gif(sumber, lapor)
    info = _probe(hasil[0])
    assert hasil[0].suffix == ".gif"
    assert _codec(info, "video") == ["gif"]
    video = info["streams"][0]
    assert video["width"] == 320 and video["r_frame_rate"] in ("12/1", "25/2")
    lapor.periksa()


def test_ambil_audio_mp3(salin):
    sumber = salin("video")
    sebelum = _hash(sumber)
    lapor = Perekam()
    hasil = media.ambil_audio(sumber, lapor, format="mp3")
    info = _probe(hasil[0])
    assert hasil[0].suffix == ".mp3"
    assert _codec(info, "audio") == ["mp3"] and _codec(info, "video") == []
    lapor.periksa()
    assert _hash(sumber) == sebelum


def test_ambil_audio_tanpa_trek(salin):
    sumber = salin("bisu")
    with pytest.raises(RuntimeError, match="Video tidak punya trek audio"):
        media.ambil_audio(sumber, lambda _p: None, format="mp3")
    assert sorted(p.name for p in sumber.parent.iterdir()) == ["bisu.mp4"]


@pytest.mark.parametrize("kunci,ext", [("video", "mp4"), ("avi", "mp4")])
def test_kompres_video(salin, kunci, ext):
    sumber = salin(kunci)
    sebelum = _hash(sumber)
    lapor = Perekam()
    hasil = media.kompres_video(sumber, lapor)
    assert hasil[0].name == f"{sumber.stem} (kompres).{ext}"
    info = _probe(hasil[0])
    assert _codec(info, "video") == ["h264"] and _codec(info, "audio") == ["aac"]
    lapor.periksa()
    assert _hash(sumber) == sebelum


def test_kompres_mkv_tetap_mkv(salin):
    mkv = media.video_ke_format(salin("video"), lambda _p: None, format="mkv")[0]
    hasil = media.kompres_video(mkv, lambda _p: None)
    assert hasil[0].name == "klip (kompres).mkv"
    assert "matroska" in _probe(hasil[0])["format"]["format_name"]


AUDIO_HARAP = {
    "mp3": ("mp3", "mp3"),
    "wav": ("pcm_s16le", "wav"),
    "ogg": ("vorbis", "ogg"),
    "flac": ("flac", "flac"),
    "m4a": ("aac", "mov,mp4"),
    "opus": ("opus", "ogg"),
}


@pytest.mark.parametrize("fmt", list(AUDIO_HARAP))
def test_audio_ke_format(salin, fmt):
    sumber = salin("wav")
    sebelum = _hash(sumber)
    lapor = Perekam()
    hasil = media.audio_ke_format(sumber, lapor, format=fmt)
    assert hasil[0].suffix == f".{fmt}"
    info = _probe(hasil[0])
    codec, wadah = AUDIO_HARAP[fmt]
    assert _codec(info, "audio") == [codec]
    assert wadah in info["format"]["format_name"]
    assert float(info["format"]["duration"]) == pytest.approx(2.0, abs=0.3)
    lapor.periksa()
    assert _hash(sumber) == sebelum


@pytest.mark.parametrize("fmt,sampul", [("flac", True), ("m4a", True), ("ogg", False), ("wav", False)])
def test_sampul_album(salin, fmt, sampul):
    hasil = media.audio_ke_format(salin("lagu"), lambda _p: None, format=fmt)
    info = _probe(hasil[0])
    assert bool(_codec(info, "video")) is sampul


def test_gagal_hapus_hasil_setengah_jadi(salin):
    sumber = salin("wav")
    with pytest.raises(RuntimeError, match="ffmpeg gagal"):
        media._jalankan(sumber, sumber.with_name("rusak.mp3"), ["-c:a", "codec_tidak_ada"],
                        lambda _p: None, 2.0)
    assert not sumber.with_name("rusak.mp3").exists()


def test_format_tidak_dikenal(salin):
    with pytest.raises(ValueError):
        media.video_ke_format(salin("video"), lambda _p: None, format="xyz")


def test_lewat_katalog(salin):
    from jelma.daftar_aksi import jalankan
    hasil = jalankan("video-ambil-mp3", salin("video"))
    assert hasil[0].suffix == ".mp3"
