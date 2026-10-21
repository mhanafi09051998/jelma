<p align="center"><img src="aset/jelma.png" width="128" alt="Ikon Jelma"></p>

# Jelma

Konversi berkas langsung dari Windows Explorer, tanpa membuka aplikasi apa pun dan sepenuhnya offline.
Pilih berkas, tekan **Ctrl + Alt + J** (atau **Shift + klik kanan → Jelma**), pilih format, selesai.
Hasilnya selalu berupa salinan baru di samping berkas asli; berkas asli tidak pernah diubah.

## Unduh

Ambil `Jelma-Setup-x.y.z.exe` dari halaman [Releases](https://github.com/mhanafi09051998/jelma/releases), lalu jalankan.
Pemasangan tidak butuh hak admin dan tidak butuh Python.

> Installer tidak ditandatangani (code signing), jadi Windows SmartScreen bisa menampilkan
> "Windows protected your PC". Klik **More info → Run anyway**.

## Cara pakai

| Cara | Langkah |
|---|---|
| Pintasan keyboard | Pilih satu atau beberapa berkas di Explorer atau Desktop, tekan **Ctrl + Alt + J**, pilih format dari menu yang muncul di kursor |
| Menu klik kanan | Tahan **Shift**, klik kanan berkas, pilih **Jelma** |

Jelma berjalan di latar belakang sebagai ikon di tray. Dari ikon itu Anda bisa menjeda pintasan,
mengganti kombinasi tombol, atau mematikan mulai otomatis.

## Yang didukung

| Jenis | Masukan | Aksi |
|---|---|---|
| Gambar | PNG, JPG, WEBP, AVIF, HEIC, BMP, GIF, TIFF, ICO | Ke PNG/JPG/WEBP/AVIF/BMP/GIF/TIFF/ICO, ke PDF, kompres, perkecil 50%, hapus metadata (GPS, kamera), baca QR code |
| Video | MP4, MKV, WEBM, MOV, AVI, M4V, WMV, FLV | Ke MP4/MKV/WEBM/MOV, ke GIF, ambil audio MP3, kompres, hapus metadata |
| Audio | MP3, WAV, OGG, FLAC, M4A, AAC, OPUS, WMA | Ke MP3/WAV/OGG/FLAC/M4A/OPUS, hapus metadata |
| PDF | PDF | Kompres, ke PNG/JPG per halaman, hapus metadata |

Hasil baca QR code disalin ke clipboard sekaligus disimpan sebagai `.txt`.

## Filosofi ikon

Ikon Jelma terinspirasi dari susunan Candi Borobudur: teras **persegi** di bawah (*Rupadhatu*, ranah yang masih
terikat bentuk) naik menuju teras **melingkar** di atas (*Arupadhatu*, ranah tanpa bentuk).

- **Persegi** di kiri-bawah: berkas dalam wujud asalnya.
- **Lingkaran** di kanan-atas: berkas dalam wujud barunya.
- **Arah naik**: perubahan sebagai pendakian, dibaca kiri ke kanan dan bawah ke atas.
- **Irisan yang dilubangi**: saat *menjelma* ("mewujudkan diri; mengambil bentuk", KBBI), bukan lagi persegi dan belum lingkaran.
- **Putih utuh**: berkas asli tidak pernah dirusak; yang berubah hanya wujudnya.

## Membangun dari kode

Butuh Python 3.12 dan [Inno Setup 6](https://jrsoftware.org/isinfo.php).

```powershell
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File build.ps1
```

`build.ps1` mengunduh FFmpeg (build GPL BtbN, diverifikasi SHA256) ke `vendor/`, menjalankan tes,
membekukan aplikasi dengan PyInstaller, lalu membuat `dist\Jelma-Setup-<versi>.exe`.

Mode pengembangan tanpa build: `python masuk.py --latar`, atau `python masuk.py gambar-ke-webp foto.png`.

## Lisensi

Kode Jelma berlisensi [MIT](LICENSE). Komponen pihak ketiga, termasuk FFmpeg (GPL v3, dijalankan sebagai
program terpisah), tercantum di [PIHAK-KETIGA.txt](PIHAK-KETIGA.txt).
