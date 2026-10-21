<img src="aset/jelma.png" width="64" alt="Ikon Jelma">

# Jelma

Jelma mengubah format berkas dari Windows Explorer. Pilih berkas, tekan Ctrl + Alt + J, lalu pilih formatnya dari menu
yang muncul di kursor. Hasilnya disimpan sebagai berkas baru di folder yang sama, dan berkas aslinya tidak diubah.
Semua proses berjalan di komputer Anda.

Unduh installer terbaru di halaman [Releases](https://github.com/mhanafi09051998/jelma/releases/latest).

<img src="docs/pintasan.png" width="720" alt="Dua foto dipilih di Explorer, Ctrl+Alt+J memunculkan menu Jelma di kursor">

## Format yang didukung

| Jenis | Masukan | Bisa diubah menjadi atau diproses dengan |
|---|---|---|
| Gambar | PNG, JPG, WEBP, AVIF, HEIC, BMP, GIF, TIFF, ICO | PNG, JPG, WEBP, AVIF, BMP, GIF, TIFF, ICO, PDF, kompres, perkecil 50%, hapus metadata, baca QR code |
| Video | MP4, MKV, WEBM, MOV, AVI, M4V, WMV, FLV | MP4, MKV, WEBM, MOV, GIF, ambil audio MP3, kompres, hapus metadata |
| Audio | MP3, WAV, OGG, FLAC, M4A, AAC, OPUS, WMA | MP3, WAV, OGG, FLAC, M4A, OPUS, hapus metadata |
| PDF | PDF | Kompres, ke PNG atau JPG per halaman, hapus metadata |

Hapus metadata membuang data seperti lokasi GPS dan merek kamera dari foto. Hasil baca QR code disalin ke clipboard
dan disimpan sebagai berkas `.txt`.

## Cara memakai

Pilih satu atau beberapa berkas di Explorer atau di Desktop, lalu tekan Ctrl + Alt + J. Kalau berkas yang dipilih
berbeda jenis, menu hanya menampilkan pilihan yang berlaku untuk semuanya.

Cara lain: tahan Shift, klik kanan berkas, lalu pilih Jelma. Menu ini sengaja hanya muncul saat Shift ditahan supaya
menu klik kanan biasa tidak bertambah panjang.

<img src="docs/klik-kanan.png" width="600" alt="Shift + klik kanan pada foto memunculkan menu Jelma dengan daftar format">

Selama berjalan, Jelma menampilkan jendela kecil di pojok kanan bawah. Klik nama berkas hasil untuk membuka foldernya.

<img src="docs/progres.png" width="320" alt="Jendela progres Jelma berisi dua berkas WEBP yang sudah jadi">

Jelma berjalan di latar belakang sebagai ikon di tray dan memakai sekitar 45 MB memori. Klik kanan ikon itu untuk
menjeda pintasan, mengganti kombinasi tombolnya, atau mematikan mulai otomatis.

## Memasang

Jalankan `Jelma-Setup-x.y.z.exe`. Installer tidak meminta hak admin dan tidak membutuhkan Python.

Installer ini belum ditandatangani, jadi Windows bisa menampilkan peringatan "Windows protected your PC". Klik
More info, lalu Run anyway. Kode lengkapnya ada di repo ini.

Ukuran installer sekitar 120 MB. Sebagian besar berasal dari FFmpeg, yang dipakai untuk video dan audio.

Untuk menghapus, buka Settings, Apps, Installed apps, lalu uninstall Jelma. Menu klik kanan dan entri mulai otomatis
ikut terhapus.

## Ikon

Bentuk ikon diambil dari susunan Candi Borobudur. Teras bawahnya persegi (Rupadhatu, ranah yang masih terikat bentuk)
dan teras atasnya melingkar (Arupadhatu, ranah tanpa bentuk). Di ikon, persegi di kiri bawah adalah berkas asli dan
lingkaran di kanan atas adalah hasilnya. Bagian yang bertumpuk dilubangi sebagai saat berkas berubah wujud, sesuai arti
"menjelma" di KBBI: mewujudkan diri, mengambil bentuk.

## Membangun dari kode

Butuh Python 3.12 dan [Inno Setup 6](https://jrsoftware.org/isinfo.php).

```powershell
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File build.ps1
```

`build.ps1` mengunduh FFmpeg (build GPL dari BtbN, dicek SHA256-nya) ke `vendor/`, menjalankan tes, membekukan
aplikasi dengan PyInstaller, lalu membuat `dist\Jelma-Setup-<versi>.exe`. Untuk mencoba tanpa build, jalankan
`python masuk.py --latar` atau `python masuk.py gambar-ke-webp foto.png`.

Daftar semua aksi ada di [`jelma/daftar_aksi.py`](jelma/daftar_aksi.py). Format baru cukup ditambahkan di sana, dan
menu klik kanan, menu pintasan, serta perintah CLI ikut memakainya.

## Lisensi

Kode Jelma memakai lisensi [MIT](LICENSE). FFmpeg (GPL v3) dijalankan sebagai program terpisah. Daftar lengkap
komponen pihak ketiga ada di [PIHAK-KETIGA.txt](PIHAK-KETIGA.txt).
