# Bangun Jelma: ffmpeg -> tes -> PyInstaller (onedir) -> installer Inno Setup.
# Pakai: powershell -ExecutionPolicy Bypass -File build.ps1 [-Tahap semua|aplikasi|installer] [-LewatiTes]
# CI menjalankan "aplikasi", menandatangani jelma.exe, lalu "installer".
param([ValidateSet('semua', 'aplikasi', 'installer')][string]$Tahap = 'semua', [switch]$LewatiTes)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$versi = (python -c "import jelma; print(jelma.__version__)").Trim()
$app = "build\dist\jelma"
Write-Host "Jelma $versi ($Tahap)"

if ($Tahap -ne 'installer') {
    & "$PSScriptRoot\ambil_ffmpeg.ps1"

    if (-not $LewatiTes) {
        python -m pytest -q
        if ($LASTEXITCODE -ne 0) { throw "Tes gagal" }
    }

    python -m PyInstaller --noconfirm --clean --windowed --onedir `
        --name jelma `
        --icon "$PSScriptRoot\aset\jelma.ico" `
        --collect-submodules jelma `
        --hidden-import pystray._win32 `
        --collect-all pypdfium2 `
        --collect-all pypdfium2_raw `
        --collect-all pillow_heif `
        --collect-all zxingcpp `
        --distpath build\dist --workpath build\kerja --specpath build `
        masuk.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller gagal" }

    New-Item -ItemType Directory -Force "$app\vendor", "$app\aset" | Out-Null
    Copy-Item vendor\ffmpeg.exe, vendor\ffprobe.exe, vendor\LICENSE.txt "$app\vendor\"
    Copy-Item aset\jelma.ico "$app\aset\"
    Copy-Item LICENSE, PIHAK-KETIGA.txt $app
}

if ($Tahap -ne 'aplikasi') {
    $iscc = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
    if (-not (Test-Path $iscc)) { $iscc = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe' }
    & $iscc /Qp "/DVersi=$versi" installer\jelma.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup gagal" }
    Get-Item "dist\Jelma-Setup-$versi.exe" | Select-Object Name, @{n='MB';e={[math]::Round($_.Length/1MB,1)}}
}
