@echo off
REM Canvas Bot Build Script
REM Builds a standalone Windows executable using PyInstaller

REM ============================================================
REM CONFIGURATION - Edit this path to change output location
REM ============================================================
set OUTPUT_PATH=C:\Users\Fonta\OneDrive - San Francisco State University\Desktop
REM ============================================================

echo ============================================================
echo Canvas Bot Build Script
echo ============================================================
echo.
echo Working directory: %CD%
echo Script directory:  %~dp0
echo Output path:       %OUTPUT_PATH%
echo.

REM ============================================================
REM Path Diagnostics
REM ============================================================
echo ------------------------------------------------------------
echo Checking required paths...
echo ------------------------------------------------------------

set FAIL=0

REM Check virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo [OK] .venv\Scripts\activate.bat
) else (
    echo [MISSING] .venv\Scripts\activate.bat
    set FAIL=1
)

REM Check icon
if exist "cb.ico" (
    echo [OK] cb.ico
) else (
    echo [MISSING] cb.ico
    set FAIL=1
)

REM Check main script
if exist "canvas_bot.py" (
    echo [OK] canvas_bot.py
) else (
    echo [MISSING] canvas_bot.py
    set FAIL=1
)

REM Check config files
if exist "config\config.yaml" (
    echo [OK] config\config.yaml
) else (
    echo [MISSING] config\config.yaml
    set FAIL=1
)

if exist "config\download_manifest.yaml" (
    echo [OK] config\download_manifest.yaml
) else (
    echo [MISSING] config\download_manifest.yaml
    set FAIL=1
)

if exist "config\re.yaml" (
    echo [OK] config\re.yaml
) else (
    echo [MISSING] config\re.yaml
    set FAIL=1
)

REM Check VBA files
if exist "tools\vba\DocumentTriggers.cls" (
    echo [OK] tools\vba\DocumentTriggers.cls
) else (
    echo [MISSING] tools\vba\DocumentTriggers.cls
    set FAIL=1
)

if exist "tools\vba\CheckIfFileExists.bas" (
    echo [OK] tools\vba\CheckIfFileExists.bas
) else (
    echo [MISSING] tools\vba\CheckIfFileExists.bas
    set FAIL=1
)

REM Check output directory
if exist "%OUTPUT_PATH%" (
    echo [OK] %OUTPUT_PATH% (output directory)
) else (
    echo [MISSING] %OUTPUT_PATH% (output directory - will try to create)
)

echo.

REM Exit if any required file is missing
if %FAIL%==1 (
    echo ------------------------------------------------------------
    echo [ERROR] One or more required files are missing!
    echo Make sure you are running this script from the project root:
    echo   cd C:\Users\Fonta\PycharmProjects\canvas-bot-v2
    echo   build.cmd
    echo ------------------------------------------------------------
    pause
    exit /b 1
)

REM ============================================================
REM Activate Virtual Environment
REM ============================================================
echo ------------------------------------------------------------
echo Activating virtual environment...
echo ------------------------------------------------------------
call .venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM ============================================================
REM Run PyInstaller
REM ============================================================
echo ------------------------------------------------------------
echo Running PyInstaller...
echo ------------------------------------------------------------
echo.

pyinstaller --onefile ^
    --name canvas_bot ^
    --console ^
    --icon=cb.ico ^
    --distpath "%OUTPUT_PATH%" ^
    --paths "%CD%" ^
    --paths "%CD%\config" ^
    --add-data "config\config.yaml;config" ^
    --add-data "config\download_manifest.yaml;config" ^
    --add-data "config\re.yaml;config" ^
    --add-data "tools\vba\DocumentTriggers.cls;tools\vba" ^
    --add-data "tools\vba\CheckIfFileExists.bas;tools\vba" ^
    canvas_bot.py

echo.
echo ============================================================
if %ERRORLEVEL% EQU 0 (
    echo [OK] Build successful!
    echo Output: %OUTPUT_PATH%\canvas_bot.exe
) else (
    echo [ERROR] Build failed with error code %ERRORLEVEL%
)
echo ============================================================

pause