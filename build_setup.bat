@echo off
setlocal EnableDelayedExpansion
cd /d %~dp0

echo.
echo ==========================================
echo Weather Notify - Build Setup
echo ==========================================
echo.
echo This builds the distributable installer:
echo   dist_setup\WeatherNotify_Setup_v0.1.21.exe
echo.

rem ------------------------------------------------------------
rem Find a usable Python on the developer PC.
rem ------------------------------------------------------------
set PYTHON_CMD=
call :check_python python
if defined PYTHON_CMD goto :python_found
call :check_python py
if defined PYTHON_CMD goto :python_found
call :check_python python3
if defined PYTHON_CMD goto :python_found

echo [ERROR] A usable Windows Python 3.11+ installation was not found.
echo Python is only required on the PC that BUILDS the installer.
echo People who install Weather Notify do NOT need Python.
pause
exit /b 1

:check_python
%1 -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
if %errorlevel%==0 set PYTHON_CMD=%1
exit /b 0

:python_found

rem ------------------------------------------------------------
rem Create/reuse the build venv.
rem ------------------------------------------------------------
if exist .venv (
    if not exist .venv\Scripts\python.exe rmdir /s /q .venv
)

if not exist .venv (
    echo Creating build environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :fail
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto :fail

echo Installing/updating PyInstaller dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt >nul
python -m pip install pyinstaller >nul
if errorlevel 1 goto :fail

rem ------------------------------------------------------------
rem Build standalone WeatherNotify.exe.
rem ------------------------------------------------------------
echo.
echo Building standalone application...
python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --hidden-import PySide6.QtPositioning ^
    --icon "assets\weather_notify.ico" ^
    --add-data "assets;assets" ^
    --name WeatherNotify ^
    main.py
if errorlevel 1 goto :fail

rem ------------------------------------------------------------
rem Find Inno Setup compiler.
rem ------------------------------------------------------------
set "ISCC="

where ISCC.exe >nul 2>nul
if %errorlevel%==0 (
    for /f "delims=" %%I in ('where ISCC.exe') do (
        if not defined ISCC set "ISCC=%%I"
    )
)

if not defined ISCC if exist "%ProgramFiles%\Inno Setup 7\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 7\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"

if not defined ISCC (
    echo.
    echo [ERROR] Inno Setup was not found.
    echo.
    echo Inno Setup is needed ONLY on your PC to create WeatherNotify_Setup.exe.
    echo The people receiving the installer do NOT need Inno Setup or Python.
    echo.
    echo Install Inno Setup, then run build_setup.bat again.
    echo Official download:
    echo   https://jrsoftware.org/isdl.php
    echo.
    echo Or with winget:
    echo   winget install --id JRSoftware.InnoSetup -e -s winget -i
    echo.
    start "" "https://jrsoftware.org/isdl.php"
    pause
    exit /b 1
)

rem ------------------------------------------------------------
rem Build installer.
rem ------------------------------------------------------------
echo.
echo Building Setup installer...
echo Using Inno Setup:
echo   %ISCC%
"%ISCC%" "setup\WeatherNotify.iss"
if errorlevel 1 goto :fail

echo.
echo ==========================================
echo Setup build completed successfully.
echo ==========================================
echo.
echo Give this file to other people:
echo   %CD%\dist_setup\WeatherNotify_Setup_v0.1.21.exe
echo.
echo Their PC does NOT need Python.
echo Their settings start empty on first install.
echo.
explorer "%CD%\dist_setup"
pause
exit /b 0

:fail
echo.
echo [ERROR] Build failed.
pause
exit /b 1
