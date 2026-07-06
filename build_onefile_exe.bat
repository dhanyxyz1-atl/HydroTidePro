@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo HydroTide Pro - Single EXE Builder
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Install Python 3.11/3.12 and try again.
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
if not exist ".venv" (
    python -m venv .venv
)

echo [2/4] Installing dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo [3/4] Building one-file HydroTidePro.exe...
pyinstaller --clean --noconfirm HydroTidePro_onefile.spec
if errorlevel 1 (
    echo Build failed. Check the PyInstaller error above.
    pause
    exit /b 1
)

echo [4/4] Done.
echo.
echo Single EXE output:
echo dist\HydroTidePro.exe
if not exist "dist\HydroTidePro.exe" (
    echo.
    echo ERROR: dist\HydroTidePro.exe was not created.
    pause
    exit /b 1
)
echo.
echo Note: one-file EXE may start slower because bundled files are extracted to a temporary folder at runtime.
echo.
pause
