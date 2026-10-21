"""Titik masuk jelma.exe.

    jelma <aksi-id> <berkas>...   konversi (dipanggil menu klik kanan)
    jelma --latar                 jalan di tray + pintasan keyboard
    jelma --pasang | --copot      daftarkan / hapus menu klik kanan dan mulai otomatis
    jelma --versi
"""
import sys

from jelma import __version__, antrean, daftar_aksi, registri


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    perintah = argv[0]
    if perintah == "--versi":
        print(__version__)
        return 0
    if perintah == "--pasang":
        registri.pasang()
        return 0
    if perintah == "--copot":
        registri.copot()
        return 0
    if perintah == "--latar":
        from jelma import latar
        return latar.main()
    if perintah not in daftar_aksi.SEMUA or len(argv) < 2:
        print(f"aksi tidak dikenal: {perintah}", file=sys.stderr)
        return 2
    tugas = [(perintah, berkas) for berkas in argv[1:]]
    if antrean.kirim(tugas):
        return 0
    return antrean.jalankan_mandiri(tugas)


if __name__ == "__main__":
    sys.exit(main())
