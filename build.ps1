param([string]$OutputDirectory = 'dist/v2.3')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$outputRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot $OutputDirectory))
$packageDirectory = [System.IO.Path]::GetFullPath((Join-Path $outputRoot 'PDF Studyo'))
$expectedDist = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'dist')) + [System.IO.Path]::DirectorySeparatorChar
if (-not $packageDirectory.StartsWith($expectedDist, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid package directory' }
# Copying a Windows DLL preserves its read-only attribute. Clear only generated files.
if (Test-Path -LiteralPath $packageDirectory) {
    Get-ChildItem -LiteralPath $packageDirectory -Recurse -File | Where-Object IsReadOnly | ForEach-Object { $_.IsReadOnly = $false }
}
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --distpath $outputRoot --name 'PDF Studyo' --collect-all pymupdf --hidden-import win32com.client --hidden-import pythoncom --collect-submodules pyhanko --collect-submodules pyhanko_certvalidator --add-data 'runtime/tessdata;runtime/tessdata' app.py
if ($LASTEXITCODE -ne 0) { throw 'Paketleme başarısız.' }
# Qt uses Windows ICU. A different ICU on PATH (e.g. from another application)
# can be picked up by PyInstaller and produces a missing-entry-point error.
$packageRoot = Join-Path $packageDirectory '_internal'
Copy-Item -LiteralPath "$env:WINDIR/System32/icuuc.dll" -Destination (Join-Path $packageRoot 'icuuc.dll') -Force
(Get-Item -LiteralPath (Join-Path $packageRoot 'icuuc.dll')).IsReadOnly = $false
Copy-Item '.venv/Lib/site-packages/PySide6/*140*.dll' -Destination $packageRoot -Force
Copy-Item -LiteralPath 'README.md' -Destination (Join-Path $packageDirectory 'KULLANIM.md') -Force
if (Test-Path -LiteralPath 'ENTEGRASYON_DURUMU.md') {
    Copy-Item -LiteralPath 'ENTEGRASYON_DURUMU.md' -Destination (Join-Path $packageDirectory 'ENTEGRASYON_DURUMU.md') -Force
}
