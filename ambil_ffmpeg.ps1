# Unduh ffmpeg + ffprobe (build GPL statis win64 dari BtbN) ke vendor\.
# Aman diulang: dilewati bila vendor\ffmpeg.exe sudah ada.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$akar = $PSScriptRoot
$vendor = Join-Path $akar 'vendor'
if (Test-Path (Join-Path $vendor 'ffmpeg.exe')) {
    Write-Host 'vendor\ffmpeg.exe sudah ada, dilewati.'
    exit 0
}

$rilis = Invoke-RestMethod -Uri 'https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/tags/latest' -Headers @{ 'User-Agent' = 'jelma' }
# Seri n8.x terbaru, GPL non-shared.
$aset = $rilis.assets |
    Where-Object { $_.name -match '^ffmpeg-n8\.(\d+)-latest-win64-gpl-8\.\d+\.zip$' } |
    Sort-Object { [int]([regex]::Match($_.name, '^ffmpeg-n8\.(\d+)').Groups[1].Value) } -Descending |
    Select-Object -First 1
if (-not $aset) { throw 'Aset ffmpeg n8.x win64 GPL tidak ditemukan di rilis latest.' }
$cek = $rilis.assets | Where-Object { $_.name -eq 'checksums.sha256' } | Select-Object -First 1
if (-not $cek) { throw 'checksums.sha256 tidak ditemukan di rilis latest.' }

$kerja = Join-Path ([IO.Path]::GetTempPath()) ('jelma-ffmpeg-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $kerja | Out-Null
try {
    $zip = Join-Path $kerja $aset.name
    Write-Host "Mengunduh $($aset.name) ..."
    Invoke-WebRequest -Uri $aset.browser_download_url -OutFile $zip -UseBasicParsing
    $daftar = (Invoke-WebRequest -Uri $cek.browser_download_url -UseBasicParsing).Content
    if ($daftar -is [byte[]]) { $daftar = [Text.Encoding]::ASCII.GetString($daftar) }

    $baris = ($daftar -split "`n") | Where-Object { $_ -match ('\s\*?' + [regex]::Escape($aset.name) + '\s*$') } | Select-Object -First 1
    if (-not $baris) { throw "Checksum untuk $($aset.name) tidak ada di checksums.sha256." }
    $harap = ($baris.Trim() -split '\s+')[0].ToLower()
    $nyata = (Get-FileHash -Path $zip -Algorithm SHA256).Hash.ToLower()
    if ($harap -ne $nyata) { throw "SHA256 tidak cocok: harap $harap, dapat $nyata" }
    Write-Host "SHA256 cocok: $nyata"

    $ekstrak = Join-Path $kerja 'isi'
    Expand-Archive -Path $zip -DestinationPath $ekstrak
    New-Item -ItemType Directory -Force -Path $vendor | Out-Null
    foreach ($nama in 'ffmpeg.exe', 'ffprobe.exe', 'LICENSE.txt') {
        $berkas = Get-ChildItem -Path $ekstrak -Recurse -File -Filter $nama | Select-Object -First 1
        if (-not $berkas) { throw "$nama tidak ada di dalam arsip." }
        Copy-Item -Path $berkas.FullName -Destination (Join-Path $vendor $nama) -Force
    }
    Write-Host "Selesai: $vendor"
}
finally {
    Remove-Item -Recurse -Force -Path $kerja -ErrorAction SilentlyContinue
}
