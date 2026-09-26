@echo off
cd /d "%~dp0"
if exist "dist\v2.3\PDF Studyo\PDF Studyo.exe" (
  start "" "dist\v2.3\PDF Studyo\PDF Studyo.exe"
) else if exist "dist\v2.2\PDF Studyo\PDF Studyo.exe" (
  start "" "dist\v2.2\PDF Studyo\PDF Studyo.exe"
) else if exist "dist\v2.1\PDF Studyo\PDF Studyo.exe" (
  start "" "dist\v2.1\PDF Studyo\PDF Studyo.exe"
) else if exist "dist\v2.0\PDF Studyo\PDF Studyo.exe" (
  start "" "dist\v2.0\PDF Studyo\PDF Studyo.exe"
) else if exist "dist\v1.2\PDF Studyo\PDF Studyo.exe" (
  start "" "dist\v1.2\PDF Studyo\PDF Studyo.exe"
) else if exist "dist\current\PDF Studyo\PDF Studyo.exe" (
  start "" "dist\current\PDF Studyo\PDF Studyo.exe"
) else if exist "dist\PDF Studyo\PDF Studyo.exe" (
  start "" "dist\PDF Studyo\PDF Studyo.exe"
) else (
  start "" ".venv\Scripts\pythonw.exe" "app.py"
)
