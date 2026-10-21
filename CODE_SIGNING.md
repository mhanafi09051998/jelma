# Kebijakan Penandatanganan Kode / Code Signing Policy

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

## Bahasa Indonesia

- Setiap installer resmi Jelma dibangun otomatis oleh GitHub Actions ([`.github/workflows/rilis.yml`](.github/workflows/rilis.yml))
  langsung dari kode di repositori ini, lalu ditandatangani lewat SignPath. Tidak ada berkas yang dibangun atau
  ditandatangani di komputer pribadi.
- Yang ditandatangani: `jelma.exe` dan `Jelma-Setup-<versi>.exe` yang diterbitkan di halaman
  [Releases](https://github.com/mhanafi09051998/jelma/releases).
- Komponen pihak ketiga (FFmpeg, pustaka Python) adalah perangkat lunak open source; daftarnya ada di
  [PIHAK-KETIGA.txt](PIHAK-KETIGA.txt).

## English

- Every official Jelma installer is built automatically by GitHub Actions from the source code in this repository
  and signed through SignPath. Nothing is built or signed on a personal machine.
- Signed files: `jelma.exe` and `Jelma-Setup-<version>.exe` published on the Releases page.

## Tim / Team roles

| Peran / Role | Anggota / Members |
|---|---|
| Committers and reviewers | [Muhammad Hanafi](https://github.com/mhanafi09051998) |
| Approvers | [Muhammad Hanafi](https://github.com/mhanafi09051998) |

Setiap permintaan tanda tangan untuk rilis disetujui manual oleh approver di SignPath.
Every release signing request is manually approved by an approver in SignPath.

## Privasi / Privacy policy

Jelma bekerja sepenuhnya offline. Program ini tidak mengirim informasi apa pun ke sistem jaringan lain.

This program will not transfer any information to other networked systems unless specifically requested by the
user or the person installing or operating it.
