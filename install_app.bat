@echo off
setlocal EnableDelayedExpansion
cd /d %~dp0

set PYTHON_CMD=
call :check_python python
if defined PYTHON_CMD goto :python_found
call :check_python py
if defined PYTHON_CMD goto :python_found
call :check_python python3
if defined PYTHON_CMD goto :python_found

echo.
echo [ERROR] A usable Windows Python installation was not found.
echo Python 3.11 or later is required for the first install/build.
pause
exit /b 1

:check_python
%1 -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
if %errorlevel%==0 set PYTHON_CMD=%1
exit /b 0

:python_found
echo.
echo ==========================================
echo Weather Notify - Install
echo ==========================================
echo.

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

echo Installing build tools...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt >nul
python -m pip install pyinstaller >nul
if errorlevel 1 goto :fail

echo Building application...
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

set "INSTALL_DIR=%LOCALAPPDATA%\Programs\WeatherNotify"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

copy /Y "dist\WeatherNotify.exe" "%INSTALL_DIR%\WeatherNotify.exe" >nul
if errorlevel 1 goto :fail
copy /Y "README.md" "%INSTALL_DIR%\README.md" >nul
copy /Y "PRIVACY.md" "%INSTALL_DIR%\PRIVACY.md" >nul
copy /Y "THIRD_PARTY_NOTICES.md" "%INSTALL_DIR%\THIRD_PARTY_NOTICES.md" >nul
copy /Y "LICENSE.md" "%INSTALL_DIR%\LICENSE.md" >nul
copy /Y "CHANGELOG.md" "%INSTALL_DIR%\CHANGELOG.md" >nul

set "TARGET=%INSTALL_DIR%\WeatherNotify.exe"
set TARGET=%TARGET%

echo Creating desktop and Start menu shortcuts...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$target=$env:TARGET;" ^
  "$ws=New-Object -ComObject WScript.Shell;" ^
  "$desktop=[Environment]::GetFolderPath('Desktop');" ^
  "$start=Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs';" ^
  "$s=$ws.CreateShortcut((Join-Path $desktop 'Weather Notify.lnk')); $s.TargetPath=$target; $s.WorkingDirectory=(Split-Path $target); $s.IconLocation=$target+',0'; $s.Save();" ^
  "$s=$ws.CreateShortcut((Join-Path $start 'Weather Notify.lnk')); $s.TargetPath=$target; $s.WorkingDirectory=(Split-Path $target); $s.IconLocation=$target+',0'; $s.Save();"
if errorlevel 1 goto :fail

echo.
echo ==========================================
echo Installation complete.
echo ==========================================
echo.
echo You can now launch Weather Notify from:
echo   - Desktop: Weather Notify
echo   - Start menu: Weather Notify
echo.
echo Installed application:
echo   %TARGET%
echo.
start "" "%TARGET%"
pause
exit /b 0

:fail
echo.
echo [ERROR] Installation failed.
pause
exit /b 1
