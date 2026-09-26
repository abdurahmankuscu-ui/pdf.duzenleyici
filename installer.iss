; PDF Stüdyo kurulum betiği (Inno Setup 6). build.ps1, ISCC.exe bulunursa bunu derler.
; Yönetici izni gerektirmez: kullanıcı klasörüne kurulur, sistem ayarlarını değiştirmez.
#define AppName "PDF Stüdyo"
#ifndef AppVersion
  #define AppVersion "2.4"
#endif
#define AppExe "PDF Studyo.exe"
#ifndef SourceDir
  #define SourceDir "dist\v" + AppVersion + "\PDF Studyo"
#endif

[Setup]
AppId={{6C4B1B0E-3F7A-4B8B-9E61-5D2C0B7E2A41}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=PDF Stüdyo
AppPublisherURL=https://github.com/abdurahmankuscu-ui/pdf.duzenleyici
AppUpdatesURL=https://github.com/abdurahmankuscu-ui/pdf.duzenleyici/releases
DefaultDirName={localappdata}\Programs\PDF Studyo
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=dist\installer
OutputBaseFilename=PDF-Studyo-{#AppVersion}-Kurulum
SetupIconFile=runtime\pdf-studyo.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Ek kısayollar:"
Name: "openwith"; Description: "PDF dosyaları için ""Birlikte aç"" menüsüne ekle"; GroupDescription: "Dosya ilişkilendirme:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} kaldır"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; Only adds an "Open with" entry for the current user; the default PDF viewer is not changed.
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExe}"" ""%1"""; Flags: uninsdeletekey; Tasks: openwith
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithList\{#AppExe}"; Flags: uninsdeletekey; Tasks: openwith

[Run]
Filename: "{app}\{#AppExe}"; Description: "{#AppName} uygulamasını başlat"; Flags: nowait postinstall skipifsilent
