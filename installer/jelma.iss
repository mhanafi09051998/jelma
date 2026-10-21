; Installer Jelma: per pengguna, tanpa hak admin.
#ifndef Versi
  #define Versi "1.0.0"
#endif

[Setup]
AppId={{6E0B7C2A-4F3D-4C1B-9A8E-5D2F1B7C9E10}
AppName=Jelma
AppVersion={#Versi}
AppPublisher=Muhammad Hanafi
AppPublisherURL=https://github.com/mhanafi09051998/jelma
DefaultDirName={localappdata}\Programs\Jelma
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Jelma-Setup-{#Versi}
SetupIconFile=..\aset\jelma.ico
UninstallDisplayIcon={app}\jelma.exe
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
CloseApplications=force

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\build\dist\jelma\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Run]
Filename: "{app}\jelma.exe"; Parameters: "--pasang"; Flags: runhidden waituntilterminated
Filename: "{app}\jelma.exe"; Parameters: "--latar"; Description: "Jalankan Jelma sekarang"; Flags: nowait postinstall

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /f /im jelma.exe"; Flags: runhidden; RunOnceId: "HentikanJelma"
Filename: "{app}\jelma.exe"; Parameters: "--copot"; Flags: runhidden waituntilterminated; RunOnceId: "CopotMenu"
