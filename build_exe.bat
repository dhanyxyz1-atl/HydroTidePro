@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo HydroTide Pro - Windows EXE Builder
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo Python tidak ditemukan. Install Python 3.11/3.12 lalu ulangi.
    pause
    exit /b 1
)

echo [1/4] Membuat virtual environment...
if not exist ".venv" (
    python -m venv .venv
)

echo [2/4] Install dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [3/4] Build HydroTidePro.exe...
pyinstaller --clean --noconfirm HydroTidePro.spec

echo [4/4] Selesai.
echo.
echo File EXE ada di:
echo dist\HydroTidePro\HydroTidePro.exe
echo.
echo Folder sample_data otomatis ikut di dist\HydroTidePro\sample_data
echo.
pause
